"""
GameEngine — ядро игровой логики.

Управляет одной партией: состояние, фазы, ночные действия, голосование,
условия победы. Не зависит от aiogram напрямую — получает callback из handlers.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Optional

from bot.config import settings
from bot.database.engine import AsyncSessionLocal
from bot.game.roles import ALL_ROLES, APPEARS_CIVILIAN, KILLER_ROLES, Role, RoleName, Team
from bot.game.balance_matrix import get_role_set


# ───────────────────────── PlayerState ───────────────────────────

@dataclass
class PlayerState:
    user_id: int
    username: str
    role: RoleName
    is_alive: bool = True
    has_vest: bool = False          # бронежилет (Броненосец / магазин)
    has_docs: bool = False          # документы (магазин)
    has_silver_bullet: bool = False # серебряная пуля (магазин)
    is_blocked: bool = False        # заблокирован (Путана / Бармен)
    is_immune_vote: bool = False    # иммунитет от голосования (Адвокат)
    poison_day: Optional[int] = None   # умрёт в конце этого дня (Отравитель)
    armorer_used_self: bool = False    # Броненосец уже выдавал бронежилет себе
    armorer_cooldown: int = 0          # осталось ночей до следующего выстрела
    necro_cooldown: int = 0            # осталось ночей до следующего воскрешения
    bartender_cooldown: int = 0        # осталось ночей до следующего блока
    player_number: int = 0             # постоянный номер игрока (1-based)
    doctor_healed_self: bool = False   # Доктор уже лечил себя
    afk_nights: int = 0                # подряд пропущенных ночей (AFK)

    @property
    def role_obj(self) -> Role:
        return ALL_ROLES[self.role]

    def display(self) -> str:
        r = self.role_obj
        return f"{r.emoji} {self.username} ({r.label})"


# Роли с кулдаунами — не наказываются за AFK
COOLDOWN_ROLES = {RoleName.ARMORER, RoleName.NECROMANCER, RoleName.BARTENDER}


# ───────────────────────── NightActions ──────────────────────────

@dataclass
class NightActions:
    """Хранит все заявки на ночные действия за одну ночь."""
    mafia_kill: Optional[int] = None            # user_id жертвы мафии (resolved)
    mafia_votes: dict = field(default_factory=dict)  # voter_uid → target_uid
    ninja_kill: Optional[int] = None            # user_id жертвы ниндзя (отдельно)
    doctor_save: Optional[int] = None           # user_id леченного
    commissioner_check: Optional[int] = None    # user_id проверяемого
    commissioner_shoot: Optional[int] = None    # user_id, в кого стреляет комиссар
    lawyer_protect: Optional[int] = None        # иммунитет от голосования
    prostitute_block: Optional[int] = None      # user_id заблокированного
    journalist_compare: Optional[tuple[int, int]] = None
    witness_watch: Optional[int] = None
    armorer_action: Optional[int] = None        # user_id получателя жилета
    necromancer_revive: Optional[int] = None    # user_id воскрешаемого
    maniac_kill: Optional[int] = None
    poisoner_poison: Optional[int] = None
    bartender_steal: Optional[int] = None       # user_id блокируемого/крадёт способность
    werewolf_kill: Optional[int] = None         # активируется после смерти мафии


# ───────────────────────── GameEngine ────────────────────────────

EventCallback = Callable[[str, dict], Coroutine]


class GameEngine:
    """
    Управляет одной партией Мафии.

    :param game_id:       ID записи в БД
    :param chat_id:       Telegram chat_id группы
    :param notify:        async callback(event_name, data) для отправки сообщений
    """

    def __init__(self, game_id: int, chat_id: int, notify: EventCallback):
        self.game_id = game_id
        self.chat_id = chat_id
        self._notify = notify

        self.players: dict[int, PlayerState] = {}   # user_id → PlayerState
        self.dead_roles: list[RoleName] = []         # для Некроманта
        self.phase: str = "lobby"                    # lobby|night|day|vote|finished
        self.day_number: int = 0
        self.night_actions = NightActions()
        self.vote_counts: dict[int, int] = {}        # user_id → число голосов (внутренний счет)
        self.votes_realtime: dict[int, int] = {}     # voter_id → target_id
        self.werewolf_active: bool = False
        self._phase_task: Optional[asyncio.Task] = None
        self.lobby_end_time: float = 0.0             # timestamp окончания лобби
        self.lobby_message_id: Optional[int] = None  # ID сообщения с набором игроков
        self.last_word_victims: list[int] = []       # Список ID тех, кто умер этой ночью

        # Записываем результаты проверок для передачи Сержантам
        self.commissioner_results: list[str] = []

        # Суд (Trial)
        self.trial_target: Optional[int] = None
        self.trial_votes: dict[int, bool] = {} # user_id -> True (like) / False (dislike)

    # ─────────────────── Setup ───────────────────────────────────

    def add_player(self, user_id: int, username: str) -> bool:
        if user_id in self.players:
            return False
        self.players[user_id] = PlayerState(user_id=user_id, username=username, role=RoleName.CIVILIAN)
        return True

    def remove_player(self, user_id: int) -> bool:
        if user_id in self.players:
            del self.players[user_id]
            return True
        return False

    def get_player_count(self) -> int:
        return len(self.players)

    def get_mafia_team_uids(self) -> list[int]:
        """Returns list of alive player IDs for Mafia family (Mafia, Don, Lawyer)."""
        mafia_roles = (RoleName.MAFIA, RoleName.DON, RoleName.LAWYER)
        return [uid for uid, p in self.players.items() 
                if p.is_alive and p.role in mafia_roles]

    def get_police_team_uids(self) -> list[int]:
        """Returns list of alive player IDs for Police (Commissioner, Sergeant)."""
        return [uid for uid, p in self.players.items() 
                if p.is_alive and p.role in (RoleName.COMMISSIONER, RoleName.SERGEANT)]

    def assign_roles(self, purchased_roles: Optional[dict[int, RoleName]] = None) -> None:
        """
        Раздаёт роли с учётом покупок.
        purchased_roles: {user_id: RoleName} — заявки на покупные роли
        """
        n = len(self.players)
        role_pool = get_role_set(n)

        # 1. Сначала обрабатываем покупки
        if purchased_roles:
            assigned_uids = {} # user_id -> RoleName

            # Обработка коллизий для уникальных ролей
            collisions: dict[RoleName, list[int]] = {}
            for uid, role_name in purchased_roles.items():
                collisions.setdefault(role_name, []).append(uid)
            
            for role_name, uids in collisions.items():
                role_info = ALL_ROLES[role_name]
                if role_info.is_unique:
                    winner_uid = random.choice(uids)
                    assigned_uids[winner_uid] = role_name
                else:
                    # Не уникальные роли (например, Мафия) могут получить все покупатели
                    for uid in uids:
                        assigned_uids[uid] = role_name

            # Назначаем роли победителям и корректируем пул
            for uid, role_name in assigned_uids.items():
                self.players[uid].role = role_name
                
                # Если роль есть в пуле — удаляем её оттуда
                if role_name in role_pool:
                    role_pool.remove(role_name)
                else:
                    # Если роли нет в пуле (например, купили Маньяка в игру на 5 чел),
                    # то мы должны убрать Мирного Жителя, чтобы общее кол-во ролей совпало с кол-вом игроков.
                    if RoleName.CIVILIAN in role_pool:
                        role_pool.remove(RoleName.CIVILIAN)
                    elif role_pool:
                        # Если вдруг даже МЖ нет (крайне редкий случай), убираем любую роль
                        role_pool.pop()

        # 2. Перемешиваем остатки пула и раздаём остальным
        random.shuffle(role_pool)
        for uid, p in self.players.items():
            if p.role == RoleName.CIVILIAN: # Еще не назначена (не покупная)
                # Важно: если игрок НЕ покупал роль, он получит что-то из остатков пула
                if role_pool:
                    p.role = role_pool.pop()

    # ─────────────────── Phase Control ───────────────────────────

    async def start_lobby(self, duration: Optional[int] = None) -> None:
        self.phase = "lobby"
        dur = duration or settings.LOBBY_DURATION
        self.lobby_end_time = asyncio.get_event_loop().time() + dur
        self._phase_task = asyncio.create_task(
            self._phase_timer(dur, self._end_lobby)
        )

    async def extend_lobby(self) -> int:
        """Добавляет 30 секунд к таймеру лобби."""
        if self.phase != "lobby":
            return 0
        if self._phase_task:
            self._phase_task.cancel()
        
        remaining = self.lobby_end_time - asyncio.get_event_loop().time()
        new_duration = max(0, remaining) + settings.EXTEND_DURATION
        self.lobby_end_time = asyncio.get_event_loop().time() + new_duration
        
        self._phase_task = asyncio.create_task(
            self._phase_timer(int(new_duration), self._end_lobby)
        )
        return int(new_duration)

    async def _end_lobby(self) -> None:
        n = self.get_player_count()
        if n < settings.MIN_PLAYERS:
            await self._notify("lobby_expired", {"count": n, "min": settings.MIN_PLAYERS})
            self.phase = "finished"
            return
        
        await self.start_game()

    async def start_game(self) -> None:
        if self._phase_task:
            self._phase_task.cancel()
        
        # Собираем лодауты игроков из БД
        purchased_roles: dict[int, RoleName] = {}
        async with AsyncSessionLocal() as session:
            from bot.database.crud import get_user, remove_item
            for uid in list(self.players.keys()):
                user = await get_user(session, uid)
                if not user: continue
                
                # 1. Роль
                if user.active_role:
                    try:
                        purchased_roles[uid] = RoleName(user.active_role)
                        # Сбрасываем активность роли после использования
                        user.active_role = None
                    except ValueError: pass
                
                # 2. Предметы (Щит, Доки, Пуля)
                p_state = self.players[uid]
                if user.active_shield:
                    if await remove_item(session, uid, "shield"):
                        p_state.has_vest = True
                        user.active_shield = False
                
                if user.active_docs:
                    if await remove_item(session, uid, "docs"):
                        p_state.has_docs = True
                        user.active_docs = False
                
                if user.active_bullet:
                    if await remove_item(session, uid, "silver_bullet"):
                        # Пуля обычно применяется при выстреле, но мы можем пометить её в p_state
                        p_state.has_silver_bullet = True  # Нужно добавить поле в PlayerState
                        user.active_bullet = False
            
            await session.commit()

        self.assign_roles(purchased_roles)
        
        # Назначаем постоянные номера игроков
        for i, p in enumerate(self.players.values(), 1):
            p.player_number = i
        
        self.phase = "night"
        self.day_number = 1
        await self._notify("game_started", {"players": list(self.players.values())})
        await self.start_night()

    async def start_night(self) -> None:
        self.phase = "night"
        self.night_actions = NightActions()
        self.last_word_victims = []  # Сброс перед новой ночью
        self._reset_night_flags()
        await self._notify("night_started", {"day": self.day_number})
        self._phase_task = asyncio.create_task(
            self._phase_timer(settings.NIGHT_DURATION, self._end_night)
        )

    async def _end_night(self) -> None:
        # --- AFK detection (before resolving actions) ---
        afk_deaths: list[dict] = []
        na = self.night_actions
        for uid, p in list(self.players.items()):
            if not p.is_alive:
                continue
            role = p.role_obj
            # Only track roles with every-night actions (not cooldown-based, not passive)
            if not role.has_night_action or p.role in COOLDOWN_ROLES:
                continue
            # Did this player submit an action this night?
            acted = self._player_acted_this_night(uid)
            if acted:
                p.afk_nights = 0
            else:
                p.afk_nights += 1
                if p.afk_nights >= 2:
                    p.is_alive = False
                    self.dead_roles.append(p.role)
                    afk_deaths.append({"user_id": uid, "role": p.role, "reasons": ["afk"]})

        # --- Night resolution ---
        deaths, vest_saves = self._resolve_night()
        if deaths:
            self.last_word_victims = [d["user_id"] for d in deaths]

        await self._notify("night_ended", {
            "deaths": deaths,
            "afk_deaths": afk_deaths,
            "vest_saves": vest_saves,
            "day": self.day_number,
        })
        if await self._check_win():
            return
        await self.start_day()

    def _player_acted_this_night(self, uid: int) -> bool:
        """Check if a player submitted any night action."""
        na = self.night_actions
        p = self.players.get(uid)
        if not p:
            return False
        match p.role:
            case RoleName.MAFIA | RoleName.DON:
                return uid in na.mafia_votes
            case RoleName.NINJA:
                return na.ninja_kill is not None
            case RoleName.DOCTOR:
                return na.doctor_save is not None
            case RoleName.COMMISSIONER:
                return na.commissioner_check is not None or na.commissioner_shoot is not None
            case RoleName.PROSTITUTE:
                return na.prostitute_block is not None
            case RoleName.JOURNALIST:
                return na.journalist_compare is not None
            case RoleName.WITNESS:
                return na.witness_watch is not None
            case RoleName.MANIAC:
                return na.maniac_kill is not None
            case RoleName.POISONER:
                return na.poisoner_poison is not None
            case RoleName.LAWYER:
                return na.lawyer_protect is not None
            case _:
                return True  # passive roles — always "acted"

    async def start_day(self) -> None:
        self.phase = "day"
        # Отравленные умирают в конце этого дня
        poisoned_deaths = [
            uid for uid, p in self.players.items()
            if p.is_alive and p.poison_day == self.day_number
        ]
        await self._notify("day_started", {
            "day": self.day_number,
            "poisoned_deaths": poisoned_deaths,
        })
        for uid in poisoned_deaths:
            self.players[uid].is_alive = False
            self.dead_roles.append(self.players[uid].role)

        if await self._check_win():
            return

        from bot.config import settings
        self._phase_task = asyncio.create_task(
            self._phase_timer(settings.DAY_DURATION, self._end_day)
        )

    async def _end_day(self) -> None:
        await self._notify("vote_started", {"day": self.day_number})
        self.vote_counts = {}
        self.phase = "vote"
        from bot.config import settings
        self._phase_task = asyncio.create_task(
            self._phase_timer(settings.VOTE_DURATION, self._end_vote)
        )

    async def _end_vote(self) -> None:
        executed = self._resolve_vote()
        self.day_number += 1
        
        # Сброс реального времени
        self.votes_realtime = {}
        
        if executed:
            # Вместо немедленной казни - на суд!
            self.trial_target = executed
            await self.start_trial()
        else:
            await self._notify("vote_ended", {
                "executed": None,
                "day": self.day_number,
            })
            if await self._check_win():
                return
            # Проверить активацию Оборотня
            self._check_werewolf_activation()
            await self.start_night()

    async def start_trial(self) -> None:
        self.phase = "trial"
        self.trial_votes = {}
        await self._notify("trial_started", {"target_id": self.trial_target})
        
        from bot.config import settings
        self._phase_task = asyncio.create_task(
            self._phase_timer(15, self._end_trial) # 15 секунд на суд
        )

    async def _end_trial(self) -> None:
        likes = sum(1 for v in self.trial_votes.values() if v is True)
        dislikes = sum(1 for v in self.trial_votes.values() if v is False)
        
        executed = None
        if likes > dislikes:
            executed = self.trial_target
            p = self.players.get(executed)
            if p:
                p.is_alive = False
                self.dead_roles.append(p.role)
                # Шут победил
                if p.role == RoleName.JESTER:
                    asyncio.create_task(self._notify("jester_wins", {"user_id": executed}))
        
        self.trial_target = None
        
        await self._notify("vote_ended", {
            "executed": executed,
            "day": self.day_number,
            "was_trial": True,
            "likes": likes,
            "dislikes": dislikes
        })

        if await self._check_win():
            return
            
        self._check_werewolf_activation()
        await self.start_night()

    def submit_trial_vote(self, user_id: int, vote: bool) -> bool:
        if self.phase != "trial":
            return False
        if user_id not in self.players or not self.players[user_id].is_alive:
            return False
        # Подсудимый не голосует за себя
        if user_id == self.trial_target:
            return False
        self.trial_votes[user_id] = vote
        return True


    # ─────────────────── Night Resolution ────────────────────────

    def _reset_night_flags(self) -> None:
        for p in self.players.values():
            p.is_blocked = False
            p.is_immune_vote = False
            # Уменьшаем кулдауны
            if p.armorer_cooldown > 0:
                p.armorer_cooldown -= 1
            if p.necro_cooldown > 0:
                p.necro_cooldown -= 1
            if p.bartender_cooldown > 0:
                p.bartender_cooldown -= 1

    def _resolve_mafia_kill(self) -> None:
        """Разрешает взвешенное голосование мафии. Дон = 2, остальные = 1."""
        na = self.night_actions
        if not na.mafia_votes:
            return
        
        # Подсчитываем взвешенные голоса
        weighted: dict[int, int] = {}  # target → total weight
        don_choice: Optional[int] = None
        
        for voter_uid, target_uid in na.mafia_votes.items():
            voter = self.players.get(voter_uid)
            if not voter:
                continue
            weight = 2 if voter.role == RoleName.DON else 1
            weighted[target_uid] = weighted.get(target_uid, 0) + weight
            if voter.role == RoleName.DON:
                don_choice = target_uid
        
        if not weighted:
            return
        
        # Находим максимум
        max_w = max(weighted.values())
        candidates = [uid for uid, w in weighted.items() if w == max_w]
        
        if len(candidates) == 1:
            na.mafia_kill = candidates[0]
        elif don_choice in candidates:
            na.mafia_kill = don_choice  # при ничьей — решение Дона
        else:
            na.mafia_kill = random.choice(candidates)

    def _resolve_night(self) -> tuple[list[dict], list[int]]:
        """
        Разрешает все ночные действия. Порядок:
        0. Голосование мафии (взвешенное)
        1. Блок (Путана / Бармен)
        2. Лечение (Доктор)
        3. Жилет Броненосца
        4. Иммунитет от голосования (Адвокат)
        5. Убийство (Мафия → Ниндзя → Маньяк → Оборотень)
        6. Воскрешение (Некромант)
        7. Яд (Отравитель — отложенная смерть)
        8. Взрыв Террориста
        Returns (deaths, vest_saves):
          deaths — list of {user_id, role, reasons: [str]}
          vest_saves — list of user_ids who were saved by vest
        """
        na = self.night_actions
        
        # 0. Разрешаем голосование мафии
        self._resolve_mafia_kill()
        
        deaths: list[dict] = []
        vest_saves: list[int] = []  # user_ids спасённых щитом

        # 1. Блок
        blocked_ids: set[int] = set()
        if na.prostitute_block and self._alive(na.prostitute_block):
            blocked_ids.add(na.prostitute_block)
            self.players[na.prostitute_block].is_blocked = True

        # Бармен крадёт способность
        if na.bartender_steal and self._alive(na.bartender_steal):
            target_p = self.players[na.bartender_steal]
            blocked_ids.add(na.bartender_steal)
            target_p.is_blocked = True
            if target_p.role_obj.team == Team.TOWN and not target_p.role_obj.has_night_action:
                pass

        # Убираем действия заблокированных
        if na.doctor_save and na.doctor_save in blocked_ids:
            na.doctor_save = None
        if na.commissioner_check and self.players.get(na.commissioner_check) and \
                self._get_actor(RoleName.COMMISSIONER) in blocked_ids:
            na.commissioner_check = None
        if na.commissioner_shoot and self._get_actor(RoleName.COMMISSIONER) in blocked_ids:
            na.commissioner_shoot = None
        if na.mafia_kill and self._get_actor(RoleName.DON) in blocked_ids:
            pass  # блок Дона не блокирует всю мафию

        # 2. Жилет от Броненосца
        if na.armorer_action and self._alive(na.armorer_action):
            arm_player = self.players[na.armorer_action]
            arm_player.has_vest = True

        # 3. Иммунитет от голосования (Адвокат)
        if na.lawyer_protect and self._alive(na.lawyer_protect):
            self.players[na.lawyer_protect].is_immune_vote = True

        # 4. Убийства — теперь с мульти-атрибуцией
        kill_targets: dict[int, list[str]] = {}  # user_id → [причины смерти]

        def _add_kill(target_uid: int, reason: str):
            kill_targets.setdefault(target_uid, []).append(reason)

        # Мафийное убийство
        main_target = na.mafia_kill or na.werewolf_kill
        if main_target and self._alive(main_target):
            p = self.players[main_target]
            killer_id = self._get_actor(RoleName.DON) or self._get_actor(RoleName.MAFIA)
            killer_state = self.players.get(killer_id)
            has_bullet = killer_state.has_silver_bullet if killer_state else False

            if na.ninja_kill == main_target:
                _add_kill(main_target, "ninja")
            else:
                if na.doctor_save == main_target and not (
                    self.players[na.doctor_save].is_blocked if na.doctor_save else False
                ):
                    pass  # спасён доктором
                elif p.has_vest and not has_bullet:
                    p.has_vest = False
                    vest_saves.append(main_target)
                else:
                    _add_kill(main_target, "mafia")

        # Ниндзя убийство (если цель != основная жертва мафии)
        if na.ninja_kill and na.ninja_kill != main_target and self._alive(na.ninja_kill):
            _add_kill(na.ninja_kill, "ninja")

        # Маньяк
        if na.maniac_kill and self._alive(na.maniac_kill):
            p = self.players[na.maniac_kill]
            killer_id = self._get_actor(RoleName.MANIAC)
            killer_state = self.players.get(killer_id)
            has_bullet = killer_state.has_silver_bullet if killer_state else False

            if na.doctor_save == na.maniac_kill:
                pass  # спасён
            elif p.has_vest and not has_bullet:
                p.has_vest = False
                vest_saves.append(na.maniac_kill)
            else:
                _add_kill(na.maniac_kill, "maniac")

        # Выстрел Комиссара
        if na.commissioner_shoot and self._alive(na.commissioner_shoot):
            p = self.players[na.commissioner_shoot]
            killer_id = self._get_actor(RoleName.COMMISSIONER)
            killer_state = self.players.get(killer_id)
            has_bullet = killer_state.has_silver_bullet if killer_state else False

            if p.has_vest and not has_bullet:
                p.has_vest = False
                vest_saves.append(na.commissioner_shoot)
            else:
                _add_kill(na.commissioner_shoot, "commissioner")

        # 5. Взрыв Террориста
        for victim_uid, reasons in list(kill_targets.items()):
            victim = self.players.get(victim_uid)
            if victim and victim.role == RoleName.TERRORIST:
                if "mafia" in reasons:
                    mafia_alive = [uid for uid, p in self.players.items()
                                   if p.is_alive and p.role in (RoleName.MAFIA, RoleName.DON)]
                    if mafia_alive:
                        boom_target = random.choice(mafia_alive)
                        _add_kill(boom_target, "terrorist_explosion")
                if "maniac" in reasons:
                    maniac_id = self._get_actor(RoleName.MANIAC)
                    if maniac_id:
                        _add_kill(maniac_id, "terrorist_explosion")

        # 6. Применяем смерти
        for uid, reasons in kill_targets.items():
            p = self.players.get(uid)
            if p and p.is_alive:
                p.is_alive = False
                self.dead_roles.append(p.role)
                deaths.append({"user_id": uid, "role": p.role, "reasons": reasons})
                if p.role == RoleName.COMMISSIONER:
                    self._promote_sergeant()

        # 7. Отравитель — ставим метку
        if na.poisoner_poison and self._alive(na.poisoner_poison):
            poisoner = self.players[na.poisoner_poison]
            if not poisoner.is_blocked:
                self.players[na.poisoner_poison].poison_day = self.day_number + 1

        # 8. Некромант воскрешает
        if na.necromancer_revive and not self._alive(na.necromancer_revive) and self.dead_roles:
            p = self.players[na.necromancer_revive]
            p.is_alive = True
            new_role = random.choice(self.dead_roles)
            p.role = new_role
            deaths = [d for d in deaths if d["user_id"] != na.necromancer_revive]

        return deaths, vest_saves

    def _resolve_vote(self) -> Optional[int]:
        """
        Дневное голосование. Возвращает user_id казнённого или None (ничья / иммунитет).
        Мэр = 2 голоса (учтено в add_vote).
        """
        if not self.vote_counts:
            return None
        max_votes = max(self.vote_counts.values())
        candidates = [uid for uid, v in self.vote_counts.items() if v == max_votes]
        if len(candidates) > 1:
            return None  # ничья

        target_id = candidates[0]
        target = self.players.get(target_id)
        if not target:
            return None

        # Иммунитет от Адвоката
        if target.is_immune_vote:
            return None

        return target_id

    # ─────────────────── Voting API ──────────────────────────────

    def add_vote(self, voter_id: int, target_id: int) -> bool:
        """Добавить голос. Мэр = 2 голоса. Мёртвые не голосуют."""
        voter = self.players.get(voter_id)
        if not voter or not voter.is_alive or self.phase != "vote":
            return False
        
        # Если уже голосовал — меняем голос (или запрещаем, по ТЗ обычно меняем)
        # Для простоты: один раз проголосовал - зафиксировано.
        if voter_id in self.votes_realtime:
            return False

        weight = 2 if voter.role == RoleName.MAYOR else 1
        self.vote_counts[target_id] = self.vote_counts.get(target_id, 0) + weight
        self.votes_realtime[voter_id] = target_id

        # Оповещаем чат через notify
        asyncio.create_task(self._notify("voted", {
            "voter_id": voter_id,
            "target_id": target_id,
            "voter": voter.username,
            "target": self.players[target_id].username if target_id in self.players else "???"
        }))
        return True

    # ─────────────────── Night Action API ────────────────────────

    def submit_night_action(self, actor_id: int, action: str, target_id: Optional[int] = None,
                             target2_id: Optional[int] = None) -> bool:
        """Получить ночной ход от игрока."""
        p = self.players.get(actor_id)
        if not p or not p.is_alive or self.phase != "night":
            return False

        # Оповещение чата о том, что ход сделан (без деталей)
        asyncio.create_task(self._notify("action_submitted", {
            "user_id": actor_id,
            "role": p.role,
            "username": p.username,
            "action": action
        }))

        match action:
            case "mafia_kill":
                # Дон и Мафия голосуют за цель (взвешенная система)
                self.night_actions.mafia_votes[actor_id] = target_id
            case "ninja_kill":
                self.night_actions.ninja_kill = target_id
            case "doctor_save":
                # Доктор может лечить себя только 1 раз
                if target_id == actor_id:
                    if p.doctor_healed_self:
                        return False  # отклоняем
                    p.doctor_healed_self = True
                self.night_actions.doctor_save = target_id
            case "commissioner_check":
                self.night_actions.commissioner_check = target_id
            case "commissioner_shoot":
                self.night_actions.commissioner_shoot = target_id
            case "lawyer_protect":
                self.night_actions.lawyer_protect = target_id
            case "prostitute_block":
                self.night_actions.prostitute_block = target_id
            case "journalist_compare":
                self.night_actions.journalist_compare = (target_id, target2_id)
            case "witness_watch":
                self.night_actions.witness_watch = target_id
            case "armorer_action":
                self.night_actions.armorer_action = target_id
            case "necromancer_revive":
                self.night_actions.necromancer_revive = target_id
            case "maniac_kill":
                self.night_actions.maniac_kill = target_id
            case "poisoner_poison":
                self.night_actions.poisoner_poison = target_id
            case "bartender_steal":
                self.night_actions.bartender_steal = target_id
            case _:
                return False
        return True

    def get_commissioner_result(self, target_id: int) -> str:
        """Результат проверки Комиссара — показывает конкретную роль."""
        p = self.players.get(target_id)
        if not p:
            return "Игрок не найден"
        role = p.role_obj
        if p.has_docs or p.role in APPEARS_CIVILIAN:
            # Документы / Оборотень — показываем как мирного
            return f"✅ {ALL_ROLES[RoleName.CIVILIAN].emoji} {ALL_ROLES[RoleName.CIVILIAN].label}"
        return f"{role.emoji} {role.label}"

    def get_journalist_result(self, uid1: int, uid2: int) -> str:
        p1 = self.players.get(uid1)
        p2 = self.players.get(uid2)
        if not p1 or not p2:
            return "Ошибка"
        same = p1.role_obj.team == p2.role_obj.team
        return "👥 Одна команда" if same else "⚔️ Разные команды"

    # ─────────────────── Win Conditions ──────────────────────────

    async def _check_win(self) -> bool:
        alive = [p for p in self.players.values() if p.is_alive]
        if not alive:
            await self._finish("nobody")
            return True

        mafia_alive = [p for p in alive if p.role_obj.team == Team.MAFIA]
        non_mafia = [p for p in alive if p.role_obj.team != Team.MAFIA]
        maniac = next((p for p in alive if p.role == RoleName.MANIAC), None)

        # 1. Маньяк победил (остался один или 1 на 1 с мирным)
        if maniac and len(alive) == 1:
            await self._finish("maniac")
            return True

        # 2. Мафия победила: мафия >= мирные (1в1, 2в2, в большинстве и т.д.)
        if mafia_alive and len(mafia_alive) >= len(non_mafia):
            await self._finish("mafia")
            return True

        # 3. Мирные победили (нет мафии, нет враждебных нейтралов)
        hostile_neutrals = [p for p in alive if p.role_obj.team == Team.NEUTRAL and p.role != RoleName.JESTER]
        if not mafia_alive and not hostile_neutrals and not self.werewolf_active:
            # Проверить спящего Оборотня
            ww = next((p for p in alive if p.role == RoleName.WEREWOLF), None)
            if not ww:
                await self._finish("town")
                return True

        return False

    async def _finish(self, winner: str) -> None:
        self.phase = "finished"

        # ВАЖНО: не отменяем задачу, если мы уже внутри неё (это вызовет CancelledError
        # на следующем await, что убьёт _notify и игра повиснет).
        current = asyncio.current_task()
        if self._phase_task and self._phase_task is not current:
            self._phase_task.cancel()
            self._phase_task = None

        from bot.game import registry
        registry.remove(self.chat_id)

        snapshot = [
            {"user_id": p.user_id, "username": p.username, "role": p.role.value, "is_alive": p.is_alive}
            for p in self.players.values()
        ]
        await self._notify("game_finished", {"winner": winner, "snapshot": snapshot})


    # ─────────────────── Utility ─────────────────────────────────

    def _alive(self, user_id: int) -> bool:
        p = self.players.get(user_id)
        return bool(p and p.is_alive)

    def _get_actor(self, role: RoleName) -> Optional[int]:
        for uid, p in self.players.items():
            if p.role == role and p.is_alive:
                return uid
        return None

    def _promote_sergeant(self) -> None:
        """Случайный живой Сержант становится Комиссаром."""
        sergeants = [uid for uid, p in self.players.items()
                     if p.is_alive and p.role == RoleName.SERGEANT]
        if sergeants:
            chosen = random.choice(sergeants)
            self.players[chosen].role = RoleName.COMMISSIONER
            asyncio.create_task(self._notify("sergeant_promoted", {"user_id": chosen}))

    def _check_werewolf_activation(self) -> None:
        """Оборотень активируется, если вся изначальная мафия мертва."""
        original_mafia_roles = {RoleName.MAFIA, RoleName.DON, RoleName.NINJA, RoleName.LAWYER}
        any_mafia_alive = any(
            p.is_alive and p.role in original_mafia_roles
            for p in self.players.values()
        )
        if not any_mafia_alive:
            ww = next(
                (p for p in self.players.values() if p.is_alive and p.role == RoleName.WEREWOLF),
                None
            )
            if ww and not self.werewolf_active:
                self.werewolf_active = True
                asyncio.create_task(self._notify("werewolf_activated", {"user_id": ww.user_id}))

    def alive_players_list(self) -> list[PlayerState]:
        return [p for p in self.players.values() if p.is_alive]

    def get_mafia_team(self) -> list[PlayerState]:
        return [p for p in self.players.values() if p.role_obj.team == Team.MAFIA]

    async def submit_last_word(self, user_id: int, text: str) -> bool:
        """Позволяет мёртвому игроку отправить одно сообщение в чат."""
        if self.phase not in ("day", "vote"):
            return False
        if user_id not in self.last_word_victims:
            return False
        
        # Одно сообщение — удаляем из списка
        self.last_word_victims.remove(user_id)
        
        await self._notify("last_word_received", {
            "user_id": user_id,
            "username": self.players[user_id].username,
            "text": text
        })
        return True

    @staticmethod
    async def _phase_timer(duration: int, callback: Callable) -> None:
        await asyncio.sleep(duration)
        await callback()
