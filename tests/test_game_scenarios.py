"""
Сценарные тесты игр на 4 и 8 игроков.

Важные особенности движка, отражённые в тестах:
  - get_commissioner_result() возвращает РЕАЛЬНУЮ роль без ✅/❌ маркеров
    (за исключением docs/Werewolf → всегда ✅ Мирный житель)
  - Голосование мафии разрешается ДО блокировки (blocking не отменяет kill-vote)
  - Блокировка ОТМЕНЯЕТ doctor_save, только если заблокирован пациент (не доктор)
  - Блокировка Комиссара → отменяет его check/shoot
  - doctor_healed_self флаг выставляется только через submit_night_action
  - _resolve_night() — синхронный метод; _end_night() — async, вызывает start_day()
"""
from __future__ import annotations

import asyncio
import pytest

from bot.game.engine import GameEngine, PlayerState, NightActions, COOLDOWN_ROLES
from bot.game.roles import RoleName, ALL_ROLES, Team
from bot.game.balance_matrix import get_role_set


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════

def make_engine(game_id: int = 1, chat_id: int = -100):
    events: list[tuple[str, dict]] = []

    async def notify(event: str, data: dict):
        events.append((event, data))

    engine = GameEngine(game_id=game_id, chat_id=chat_id, notify=notify)
    return engine, events


def add_player(engine: GameEngine, user_id: int, role: RoleName, **kw) -> PlayerState:
    ps = PlayerState(user_id=user_id, username=f"P{user_id}", role=role, **kw)
    ps.player_number = user_id
    engine.players[user_id] = ps
    return ps


def run(coro):
    """Запускает корутину в новом цикле событий, затем отменяет все задачи."""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(coro)
        # Отменяем pending tasks (таймеры фаз)
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        return result
    finally:
        loop.close()


# ─── Ярлыки ролей для проверок ─────────────────────────────────
_CIVILIAN_RESULT = f"{ALL_ROLES[RoleName.CIVILIAN].emoji} {ALL_ROLES[RoleName.CIVILIAN].label}"
_DON_RESULT      = f"{ALL_ROLES[RoleName.DON].emoji} {ALL_ROLES[RoleName.DON].label}"
_MAFIA_RESULT    = f"{ALL_ROLES[RoleName.MAFIA].emoji} {ALL_ROLES[RoleName.MAFIA].label}"
_DOCTOR_RESULT   = f"{ALL_ROLES[RoleName.DOCTOR].emoji} {ALL_ROLES[RoleName.DOCTOR].label}"


# ─── 4-player: IDs ────────────────────────────────────────────
# balance_matrix[4] = [COM, C, C, DON]
P4_COM = 1   # Commissioner
P4_C1  = 2   # Civilian
P4_C2  = 3   # Civilian
P4_DON = 4   # Don


def build_4p() -> tuple[GameEngine, list]:
    engine, events = make_engine()
    add_player(engine, P4_COM, RoleName.COMMISSIONER)
    add_player(engine, P4_C1,  RoleName.CIVILIAN)
    add_player(engine, P4_C2,  RoleName.CIVILIAN)
    add_player(engine, P4_DON, RoleName.DON)
    engine.phase = "night"
    engine.day_number = 1
    engine.night_actions = NightActions()
    return engine, events


# ─── 8-player: IDs ────────────────────────────────────────────
# balance_matrix[8] = [COM, C, C, DON, DOC, MAF, PRO, MAF]
P8_COM  = 1
P8_C1   = 2
P8_C2   = 3
P8_DON  = 4
P8_DOC  = 5
P8_MAF1 = 6
P8_PRO  = 7
P8_MAF2 = 8


def build_8p() -> tuple[GameEngine, list]:
    engine, events = make_engine(game_id=8, chat_id=-108)
    add_player(engine, P8_COM,  RoleName.COMMISSIONER)
    add_player(engine, P8_C1,   RoleName.CIVILIAN)
    add_player(engine, P8_C2,   RoleName.CIVILIAN)
    add_player(engine, P8_DON,  RoleName.DON)
    add_player(engine, P8_DOC,  RoleName.DOCTOR)
    add_player(engine, P8_MAF1, RoleName.MAFIA)
    add_player(engine, P8_PRO,  RoleName.PROSTITUTE)
    add_player(engine, P8_MAF2, RoleName.MAFIA)
    engine.phase = "night"
    engine.day_number = 1
    engine.night_actions = NightActions()
    return engine, events


# ════════════════════════════════════════════════════════════════
#  4-PLAYER TESTS
# ════════════════════════════════════════════════════════════════

class Test4PlayerBalance:
    """Balance matrix: 4 игрока."""

    def test_balance_matrix_4_composition(self):
        roles = get_role_set(4)
        assert len(roles) == 4

    def test_balance_matrix_4_has_commissioner_and_don(self):
        roles = get_role_set(4)
        assert RoleName.COMMISSIONER in roles
        assert RoleName.DON in roles

    def test_balance_matrix_4_no_regular_mafia(self):
        """4-игровая раздача: только Дон, без рядовой Мафии."""
        roles = get_role_set(4)
        assert RoleName.MAFIA not in roles

    def test_4p_engine_has_4_players(self):
        engine, _ = build_4p()
        assert len(engine.players) == 4

    def test_4p_teams(self):
        engine, _ = build_4p()
        town  = [p for p in engine.players.values() if p.role_obj.team == Team.TOWN]
        mafia = [p for p in engine.players.values() if p.role_obj.team == Team.MAFIA]
        assert len(town)  == 3   # COM + 2 Civilian
        assert len(mafia) == 1   # Don


class Test4PlayerTownWins:
    """Город побеждает в 4-игровых сценариях."""

    def test_commissioner_shoots_don_town_wins(self):
        """Комиссар стреляет в Дона → Город побеждает сразу."""
        engine, events = build_4p()
        engine.night_actions.commissioner_shoot = P4_DON

        run(engine._end_night())

        assert engine.players[P4_DON].is_alive is False
        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "town"

    def test_check_win_no_mafia_town_wins(self):
        """_check_win: 0 мафии → победа города."""
        engine, events = build_4p()
        engine.players[P4_DON].is_alive = False

        result = run(engine._check_win())

        assert result is True
        finished = [e for e in events if e[0] == "game_finished"]
        assert finished[0][1]["winner"] == "town"

    def test_trial_execution_of_don_ends_game(self):
        """Суд: казнят Дона → Город побеждает."""
        engine, events = build_4p()
        engine.phase = "trial"
        engine.trial_target = P4_DON
        engine.trial_votes = {P4_COM: True, P4_C1: True, P4_C2: True}

        run(engine._end_trial())

        assert engine.players[P4_DON].is_alive is False
        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "town"

    def test_trial_pardon_no_win(self):
        """Суд: Дона помиловали → игра продолжается."""
        engine, events = build_4p()
        engine.phase = "trial"
        engine.trial_target = P4_DON
        engine.trial_votes = {P4_COM: False, P4_C1: False, P4_C2: False}

        run(engine._end_trial())

        assert engine.players[P4_DON].is_alive is True
        assert len([e for e in events if e[0] == "game_finished"]) == 0


class Test4PlayerMafiaWins:
    """Мафия побеждает в 4-игровых сценариях."""

    def test_1v1_mafia_wins(self):
        """1 горожанин, 1 мафия → победа мафии."""
        engine, events = build_4p()
        engine.players[P4_C1].is_alive = False
        engine.players[P4_C2].is_alive = False

        result = run(engine._check_win())

        assert result is True
        finished = [e for e in events if e[0] == "game_finished"]
        assert finished[0][1]["winner"] == "mafia"

    def test_2v2_parity_mafia_wins(self):
        """2 мафия >= 2 город → победа мафии."""
        engine, events = make_engine()
        add_player(engine, 1, RoleName.CIVILIAN)
        add_player(engine, 2, RoleName.CIVILIAN)
        add_player(engine, 3, RoleName.DON)
        add_player(engine, 4, RoleName.MAFIA)
        engine.phase = "night"

        result = run(engine._check_win())

        assert result is True
        assert [e for e in events if e[0] == "game_finished"][0][1]["winner"] == "mafia"

    def test_don_kills_civilian_game_continues(self):
        """Дон убивает мирного → 3 живых, игра продолжается."""
        engine, events = build_4p()
        engine.night_actions.mafia_votes[P4_DON] = P4_C1

        run(engine._end_night())

        assert engine.players[P4_C1].is_alive is False
        # Живы: COM, C2, DON — 2 town, 1 mafia → продолжается
        assert len([e for e in events if e[0] == "game_finished"]) == 0

    def test_don_kills_commissioner_game_continues(self):
        """Дон убивает Комиссара → 2 civilians vs 1 Don → игра продолжается (2 > 1)."""
        engine, events = build_4p()
        engine.night_actions.mafia_votes[P4_DON] = P4_COM

        run(engine._end_night())

        assert engine.players[P4_COM].is_alive is False
        # 2 town (C1, C2) vs 1 mafia (DON) → мафия НЕ победила
        assert len([e for e in events if e[0] == "game_finished"]) == 0

    def test_don_kills_twice_reaches_1v1_mafia_wins(self):
        """Дон убивает C1 (ночь 1), C2 (ночь 2) → 1v1 → Мафия побеждает."""
        engine, events = build_4p()

        # Ночь 1: убиваем C1
        engine.night_actions.mafia_votes[P4_DON] = P4_C1
        run(engine._end_night())
        assert engine.players[P4_C1].is_alive is False
        assert len([e for e in events if e[0] == "game_finished"]) == 0

        # Ночь 2: убиваем C2 → COM vs DON = 1v1
        engine.phase = "night"
        engine.day_number = 2
        engine.night_actions = NightActions()
        engine.night_actions.mafia_votes[P4_DON] = P4_C2
        run(engine._end_night())

        assert engine.players[P4_C2].is_alive is False
        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "mafia"

    def test_wrong_trial_then_1v1_mafia_wins(self):
        """Ночь 1: Дон убивает C1. День: город казнит C2 → 1v1 → мафия."""
        engine, events = build_4p()

        # Ночь 1
        engine.night_actions.mafia_votes[P4_DON] = P4_C1
        run(engine._end_night())
        assert engine.players[P4_C1].is_alive is False

        # Суд: казнят C2 (ошибочно)
        engine.phase = "trial"
        engine.trial_target = P4_C2
        engine.trial_votes = {P4_COM: True, P4_DON: True}
        run(engine._end_trial())

        assert engine.players[P4_C2].is_alive is False
        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "mafia"


class Test4PlayerCommissioner:
    """Проверки и выстрелы Комиссара."""

    def test_check_don_shows_don_label(self):
        """Комиссар видит реальную роль Дона (не просто 'мафия')."""
        engine, _ = build_4p()
        result = engine.get_commissioner_result(P4_DON)
        assert result == _DON_RESULT

    def test_check_civilian_shows_civilian_label(self):
        """Комиссар видит реальную роль Мирного."""
        engine, _ = build_4p()
        result = engine.get_commissioner_result(P4_C1)
        assert result == _CIVILIAN_RESULT

    def test_player_with_docs_appears_as_civilian(self):
        """Игрок с документами → комиссар видит «✅ Мирный житель»."""
        engine, _ = build_4p()
        engine.players[P4_DON].has_docs = True
        result = engine.get_commissioner_result(P4_DON)
        assert result == f"✅ {_CIVILIAN_RESULT}"

    def test_commissioner_shoot_kills_target(self):
        """Выстрел Комиссара убивает цель."""
        engine, _ = build_4p()
        engine.night_actions.commissioner_shoot = P4_DON

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P4_DON in dead_ids

    def test_commissioner_shoot_and_don_kill_simultaneously(self):
        """COM стреляет в C1, Дон убивает C2 — оба умирают."""
        engine, _ = build_4p()
        engine.night_actions.commissioner_shoot = P4_C1
        engine.night_actions.mafia_votes[P4_DON] = P4_C2

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P4_C1 in dead_ids
        assert P4_C2 in dead_ids


# ════════════════════════════════════════════════════════════════
#  8-PLAYER TESTS
# ════════════════════════════════════════════════════════════════

class Test8PlayerBalance:
    """Balance matrix: 8 игроков."""

    def test_balance_matrix_8_composition(self):
        roles = get_role_set(8)
        assert len(roles) == 8

    def test_balance_matrix_8_has_doctor_and_prostitute(self):
        roles = get_role_set(8)
        assert RoleName.DOCTOR in roles
        assert RoleName.PROSTITUTE in roles

    def test_balance_matrix_8_three_mafia_total(self):
        """8 игроков = Don + MAF + MAF = 3 мафии."""
        roles = get_role_set(8)
        mafia_count = roles.count(RoleName.MAFIA) + roles.count(RoleName.DON)
        assert mafia_count == 3

    def test_8p_engine_correct_teams(self):
        engine, _ = build_8p()
        town  = [p for p in engine.players.values() if p.role_obj.team == Team.TOWN]
        mafia = [p for p in engine.players.values() if p.role_obj.team == Team.MAFIA]
        assert len(town) == 5   # COM, C, C, DOC, PRO
        assert len(mafia) == 3  # DON, MAF, MAF


class Test8PlayerDoctorMechanics:
    """Доктор: спасение и самолечение."""

    def test_doctor_saves_civilian_from_mafia(self):
        """Доктор лечит C1, мафия атакует C1 → C1 жив."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1
        engine.night_actions.doctor_save = P8_C1
        # путана блокирует кого-то другого, не C1
        engine.night_actions.prostitute_block = P8_C2

        deaths, _ = engine._resolve_night()

        assert engine.players[P8_C1].is_alive is True
        assert len([d for d in deaths if d["user_id"] == P8_C1]) == 0

    def test_doctor_wrong_target_victim_dies(self):
        """Доктор лечит C2, мафия атакует C1 → C1 умирает."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.doctor_save = P8_C2

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids

    def test_prostitute_blocks_doctor_patient_cancels_save(self):
        """
        Путана блокирует пациента доктора (C1).
        → doctor_save аннулируется, мафия убивает C1.
        """
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.doctor_save = P8_C1
        engine.night_actions.prostitute_block = P8_C1  # блокирует ПАЦИЕНТА

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids

    def test_doctor_self_heal_via_submit_action(self):
        """submit_night_action doctor_save=self → флаг doctor_healed_self = True."""
        engine, _ = build_8p()
        engine.phase = "night"

        async def _submit():
            return engine.submit_night_action(P8_DOC, "doctor_save", P8_DOC)

        ok = run(_submit())

        assert ok is True
        assert engine.players[P8_DOC].doctor_healed_self is True
        assert engine.night_actions.doctor_save == P8_DOC

    def test_doctor_second_self_heal_rejected(self):
        """Второй submit doctor_save=self — возвращает False."""
        engine, _ = build_8p()
        engine.phase = "night"
        engine.players[P8_DOC].doctor_healed_self = True

        async def _submit():
            return engine.submit_night_action(P8_DOC, "doctor_save", P8_DOC)

        ok = run(_submit())

        assert ok is False
        assert engine.night_actions.doctor_save is None

    def test_doctor_self_heal_saves_from_mafia(self):
        """Доктор лечит себя, мафия атакует его → выживает."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_DOC
        engine.night_actions.mafia_votes[P8_MAF1] = P8_DOC
        engine.night_actions.doctor_save = P8_DOC

        deaths, _ = engine._resolve_night()

        assert engine.players[P8_DOC].is_alive is True


class Test8PlayerProstituteBlocking:
    """Путана блокирует ночные способности (не kill-votes мафии)."""

    def test_prostitute_blocks_commissioner_check(self):
        """Путана блокирует Комиссара → commissioner_check аннулируется."""
        engine, _ = build_8p()
        engine.night_actions.commissioner_check = P8_C1
        engine.night_actions.prostitute_block = P8_COM  # блокируем Комиссара
        engine.night_actions.mafia_votes[P8_DON] = P8_C2

        engine._resolve_night()

        assert engine.night_actions.commissioner_check is None

    def test_prostitute_blocks_commissioner_shoot(self):
        """Путана блокирует Комиссара → commissioner_shoot аннулируется."""
        engine, _ = build_8p()
        engine.night_actions.commissioner_shoot = P8_MAF1
        engine.night_actions.prostitute_block = P8_COM

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_MAF1 not in dead_ids

    def test_mafia_kill_vote_unaffected_by_don_block(self):
        """
        Голосование мафии разрешается ДО блокировки.
        Если Дон заблокирован, его vote всё равно был засчитан.
        """
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON] = P8_C1  # Дон голосует
        engine.night_actions.prostitute_block = P8_DON    # потом путана блокирует Дона

        deaths, _ = engine._resolve_night()

        # Дон (вес 2) → C1 умирает несмотря на блокировку
        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids

    def test_blocking_mafia_member_does_not_remove_kill_vote(self):
        """Блок рядового мафиози не отменяет его vote (vote уже подсчитан)."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.prostitute_block = P8_MAF1  # блокируем MAF1

        deaths, _ = engine._resolve_night()

        # Обоих votes уже посчитали → C1 умирает
        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids


class Test8PlayerShield:
    """Бронежилет в 8-игровом режиме."""

    def test_vest_saves_from_mafia_kill(self):
        """Щит спасает C1 от убийства мафии."""
        engine, _ = build_8p()
        engine.players[P8_C1].has_vest = True
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1

        deaths, vest_saves = engine._resolve_night()

        assert engine.players[P8_C1].is_alive is True
        assert engine.players[P8_C1].has_vest is False
        assert P8_C1 in vest_saves

    def test_vest_burns_after_save(self):
        """После срабатывания has_vest = False."""
        engine, _ = build_8p()
        engine.players[P8_C1].has_vest = True
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1

        engine._resolve_night()

        assert engine.players[P8_C1].has_vest is False

    def test_vest_on_non_attacked_player_stays(self):
        """Щит C2 (не атакованного) не тратится."""
        engine, _ = build_8p()
        engine.players[P8_C2].has_vest = True
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1

        engine._resolve_night()

        assert engine.players[P8_C2].has_vest is True

    def test_silver_bullet_bypasses_vest(self):
        """Серебряная пуля Комиссара пробивает щит."""
        engine, _ = build_8p()
        engine.players[P8_C1].has_vest = True
        engine.players[P8_COM].has_silver_bullet = True
        engine.night_actions.commissioner_shoot = P8_C1

        deaths, vest_saves = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids
        assert P8_C1 not in vest_saves


class Test8PlayerCommissioner:
    """Комиссар в 8-игровом режиме."""

    def test_check_don_shows_don_label(self):
        engine, _ = build_8p()
        result = engine.get_commissioner_result(P8_DON)
        assert result == _DON_RESULT

    def test_check_mafia_member_shows_mafia_label(self):
        engine, _ = build_8p()
        result = engine.get_commissioner_result(P8_MAF1)
        assert result == _MAFIA_RESULT

    def test_check_civilian_shows_civilian_label(self):
        engine, _ = build_8p()
        result = engine.get_commissioner_result(P8_C1)
        assert result == _CIVILIAN_RESULT

    def test_check_doctor_shows_doctor_label(self):
        engine, _ = build_8p()
        result = engine.get_commissioner_result(P8_DOC)
        assert result == _DOCTOR_RESULT

    def test_commissioner_shoot_kills_mafia(self):
        engine, events = build_8p()
        engine.night_actions.commissioner_shoot = P8_MAF1

        run(engine._end_night())

        assert engine.players[P8_MAF1].is_alive is False

    def test_commissioner_shoot_and_mafia_kill_same_night(self):
        """COM стреляет в MAF1, мафия убивает C1 — одновременно."""
        engine, _ = build_8p()
        engine.night_actions.commissioner_shoot = P8_MAF1
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_MAF1 in dead_ids
        assert P8_C1   in dead_ids


class Test8PlayerWinConditions:
    """Условия победы в 8-игровом режиме."""

    def test_town_wins_all_mafia_dead(self):
        engine, events = build_8p()
        engine.players[P8_DON].is_alive  = False
        engine.players[P8_MAF1].is_alive = False
        engine.players[P8_MAF2].is_alive = False

        result = run(engine._check_win())

        assert result is True
        assert [e for e in events if e[0] == "game_finished"][0][1]["winner"] == "town"

    def test_mafia_wins_at_parity_2v2(self):
        """2 town vs 2 mafia → паритет → победа мафии."""
        engine, events = build_8p()
        engine.players[P8_C2].is_alive   = False
        engine.players[P8_DOC].is_alive  = False
        engine.players[P8_PRO].is_alive  = False
        engine.players[P8_MAF2].is_alive = False

        result = run(engine._check_win())

        assert result is True
        assert [e for e in events if e[0] == "game_finished"][0][1]["winner"] == "mafia"

    def test_game_continues_at_start(self):
        """5 town : 3 mafia → игра продолжается."""
        engine, events = build_8p()
        result = run(engine._check_win())
        assert result is False

    def test_game_continues_after_one_kill(self):
        """4 town : 3 mafia → продолжается."""
        engine, events = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1

        run(engine._end_night())

        assert engine.players[P8_C1].is_alive is False
        assert len([e for e in events if e[0] == "game_finished"]) == 0

    def test_mafia_wins_after_two_nights(self):
        """Ночь 1 → 4v3, Ночь 2 → 3v3 → мафия побеждает."""
        engine, events = build_8p()

        # Ночь 1: убиваем C1
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1
        run(engine._end_night())
        assert engine.players[P8_C1].is_alive is False
        assert len([e for e in events if e[0] == "game_finished"]) == 0

        # Ночь 2: убиваем C2
        engine.phase = "night"
        engine.day_number = 2
        engine.night_actions = NightActions()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C2
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C2
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C2
        run(engine._end_night())

        assert engine.players[P8_C2].is_alive is False
        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "mafia"

    def test_town_wins_by_executing_all_three_mafia(self):
        """Суды: казнят MAF1, DON, MAF2 → Город побеждает."""
        engine, events = build_8p()

        for target in [P8_MAF1, P8_DON, P8_MAF2]:
            engine.phase = "trial"
            engine.trial_target = target
            engine.trial_votes = {
                P8_COM: True, P8_C1: True, P8_C2: True,
                P8_DOC: True, P8_PRO: True,
            }
            run(engine._end_trial())
            assert engine.players[target].is_alive is False

        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        assert finished[0][1]["winner"] == "town"


class Test8PlayerMultiKill:
    """Несколько убийц — причины смерти."""

    def test_all_three_mafia_vote_same_target(self):
        """Все 3 мафиози → C1 умирает с причиной 'mafia'."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1

        deaths, _ = engine._resolve_night()

        c1 = [d for d in deaths if d["user_id"] == P8_C1]
        assert len(c1) == 1
        assert "mafia" in c1[0]["reasons"]

    def test_commissioner_and_mafia_kill_different_targets(self):
        """COM убивает MAF1, мафия убивает C1 — разные причины."""
        engine, _ = build_8p()
        engine.night_actions.commissioner_shoot = P8_MAF1
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C1

        deaths, _ = engine._resolve_night()

        dead = {d["user_id"]: d for d in deaths}
        assert P8_C1   in dead
        assert P8_MAF1 in dead
        assert "mafia"        in dead[P8_C1]["reasons"]
        assert "commissioner" in dead[P8_MAF1]["reasons"]

    def test_don_weight_2_wins_over_mafia_weight_1(self):
        """Дон (вес 2) голосует за C1, MAF1 (вес 1) за C2 → C1 умирает."""
        engine, _ = build_8p()
        engine.night_actions.mafia_votes[P8_DON]  = P8_C1  # вес 2
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C2  # вес 1

        deaths, _ = engine._resolve_night()

        dead_ids = [d["user_id"] for d in deaths]
        assert P8_C1 in dead_ids
        assert P8_C2 not in dead_ids


class Test8PlayerAFK:
    """AFK-система в 8-игровом режиме."""

    def test_first_missed_night_increments_counter(self):
        """Первый пропуск: afk_nights += 1, игрок жив."""
        engine, _ = build_8p()
        doc = engine.players[P8_DOC]

        run(engine._end_night())

        assert doc.is_alive is True
        assert doc.afk_nights == 1

    def test_second_missed_night_kills_player(self):
        """Второй пропуск подряд → игрок умирает."""
        engine, events = build_8p()
        doc = engine.players[P8_DOC]
        doc.afk_nights = 1

        run(engine._end_night())

        assert doc.is_alive is False
        night_data = [e[1] for e in events if e[0] == "night_ended"]
        assert night_data
        afk_ids = [d["user_id"] for d in night_data[0].get("afk_deaths", [])]
        assert P8_DOC in afk_ids

    def test_acting_resets_afk_counter(self):
        """Если доктор сделал ход → afk_nights = 0."""
        engine, _ = build_8p()
        engine.players[P8_DOC].afk_nights = 1
        engine.night_actions.doctor_save = P8_C1

        run(engine._end_night())

        assert engine.players[P8_DOC].afk_nights == 0
        assert engine.players[P8_DOC].is_alive is True

    def test_prostitute_acting_resets_afk(self):
        """Путана сделала ход → afk_nights = 0."""
        engine, _ = build_8p()
        engine.players[P8_PRO].afk_nights = 1
        engine.night_actions.prostitute_block = P8_C2
        engine.night_actions.doctor_save = P8_C1

        run(engine._end_night())

        assert engine.players[P8_PRO].afk_nights == 0
        assert engine.players[P8_PRO].is_alive is True

    def test_civilian_no_night_action_never_afk_dies(self):
        """Мирный не наказывается за AFK (нет ночного действия)."""
        engine, _ = build_8p()
        engine.players[P8_C1].afk_nights = 99
        engine.night_actions.doctor_save = P8_C2
        engine.night_actions.prostitute_block = P8_C2

        run(engine._end_night())

        assert engine.players[P8_C1].is_alive is True

    def test_cooldown_role_not_penalized_for_afk(self):
        """Роли с кулдауном (Armorer) не наказываются за пропуск."""
        engine, _ = make_engine(game_id=99, chat_id=-999)
        add_player(engine, 1, RoleName.COMMISSIONER)
        add_player(engine, 2, RoleName.CIVILIAN)
        add_player(engine, 3, RoleName.ARMORER)
        add_player(engine, 4, RoleName.DON)
        engine.phase = "night"
        engine.day_number = 1
        engine.night_actions = NightActions()

        engine.players[3].afk_nights = 99

        run(engine._end_night())

        assert engine.players[3].is_alive is True


class Test8PlayerFullNightCycle:
    """Полный цикл ночи: события и итоги."""

    def test_night_ended_event_is_fired(self):
        """После _end_night() в events есть 'night_ended'."""
        engine, events = build_8p()
        engine.night_actions.doctor_save      = P8_C1
        engine.night_actions.prostitute_block = P8_C2
        engine.night_actions.mafia_votes[P8_DON]  = P8_C2
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C2

        run(engine._end_night())

        night_ended = [e for e in events if e[0] == "night_ended"]
        assert len(night_ended) >= 1
        assert "deaths"    in night_ended[0][1]
        assert "vest_saves" in night_ended[0][1]

    def test_snapshot_roles_are_strings(self):
        """В snapshot финала роли — строки, не enum-объекты."""
        engine, events = build_8p()
        engine.players[P8_DON].is_alive  = False
        engine.players[P8_MAF1].is_alive = False
        engine.players[P8_MAF2].is_alive = False

        run(engine._check_win())

        finished = [e for e in events if e[0] == "game_finished"]
        assert len(finished) == 1
        for p in finished[0][1]["snapshot"]:
            assert isinstance(p["role"], str), \
                f"role должна быть str, получили {type(p['role'])}"

    def test_all_active_roles_acting_resets_afk(self):
        """Если все активные роли сделали ходы, ни у кого не растёт afk_nights."""
        engine, _ = build_8p()

        # Все активные роли делают ходы
        engine.night_actions.commissioner_check   = P8_MAF1
        engine.night_actions.doctor_save          = P8_C1
        engine.night_actions.prostitute_block     = P8_COM
        engine.night_actions.mafia_votes[P8_DON]  = P8_C2
        engine.night_actions.mafia_votes[P8_MAF1] = P8_C2
        engine.night_actions.mafia_votes[P8_MAF2] = P8_C2

        run(engine._end_night())

        active_roles = {RoleName.COMMISSIONER, RoleName.DOCTOR,
                        RoleName.PROSTITUTE, RoleName.MAFIA, RoleName.DON}
        for uid, p in engine.players.items():
            if p.role in active_roles and p.is_alive:
                assert p.afk_nights == 0, \
                    f"{p.role} сделал ход, но afk_nights={p.afk_nights}"
