"""
Notify dispatcher — получает события от GameEngine и отправляет сообщения в Telegram.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.game.engine import GameEngine, PlayerState
from bot.game.roles import ALL_ROLES, RoleName, Team
from bot.keyboards.game_kb import day_vote_keyboard, players_target_keyboard
from bot.database.crud import (
    finish_game, get_game_with_players, log_transaction,
    update_balance, get_or_create_user
)
from bot.database.engine import AsyncSessionLocal
from bot.config import settings
from bot.game import registry
from bot.i18n import t, get_lang, get_role_label, get_role_desc, get_role_goal, get_team_name


def _chat_kb(chat_id: int):
    """Клавиатура с кнопкой 'Перейти в чат'."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    chat_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}"
    builder.row(InlineKeyboardButton(text="💬 Перейти в чат", url=chat_link))
    return builder.as_markup()


def _with_chat_link(kb, chat_id: int, engine=None):
    """Добавляет кнопку 'Перейти в чат' к существующей клавиатуре."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from bot.game import registry as _reg
    if engine is None:
        engine = _reg.get(chat_id)
    msg_id = (engine.lobby_message_id or 1) if engine else 1
    builder = InlineKeyboardBuilder.from_markup(kb)
    builder.row(InlineKeyboardButton(text="💬 Перейти в чат",
                                     url=f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"))
    return builder.as_markup()


async def make_notify(bot: Bot, chat_id: int, engine: GameEngine):
    """Возвращает async notify callback для GameEngine."""

    async def notify(event: str, data: dict):
        handlers = {
            "game_started": _on_game_started,
            "night_started": _on_night_started,
            "night_ended": _on_night_ended,
            "day_started": _on_day_started,
            "vote_started": _on_vote_started,
            "trial_started": _on_trial_started,
            "vote_ended": _on_vote_ended,
            "game_finished": _on_game_finished,
            "sergeant_promoted": lambda b, c, d: _on_sergeant_promoted(b, c, d),
            "werewolf_activated": _on_werewolf_activated,
            "lobby_expired": _on_lobby_expired,
            "jester_wins": _on_jester_wins,
            "action_submitted": lambda b, c, d: _on_action_submitted(b, c, d),
            "voted": lambda b, c, d: _on_voted(b, c, d),
            "last_word_received": lambda b, c, d: _on_last_word_received(b, c, d),
        }

        handler = handlers.get(event)
        if handler:
            try:
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) == 4:
                    await handler(bot, chat_id, engine, data)
                else:
                    await handler(bot, chat_id, data)
            except Exception as e:
                logging.getLogger(__name__).error(f"Notify error [{event}]: {e}", exc_info=True)

    return notify


async def _on_game_started(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    players: list[PlayerState] = data["players"]
    lang = await get_lang(chat_id)
    
    # 1. Откепляем и удаляем сообщение лобби
    if engine.lobby_message_id:
        try:
            await bot.unpin_chat_message(chat_id, engine.lobby_message_id)
        except Exception: pass
        try:
            await bot.delete_message(chat_id, engine.lobby_message_id)
        except Exception: pass
        engine.lobby_message_id = None

    text = t("game_started", lang, count=len(players))
    
    msg = await bot.send_message(chat_id, text, parse_mode="HTML")
    try:
        await bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
    except Exception: pass

    # Отправляем роль каждому в ЛС
    for p in players:
        role = ALL_ROLES[p.role]
        role_text = t("your_role", lang,
                       emoji=role.emoji,
                       label=get_role_label(role.name.value, lang),
                       description=get_role_desc(role.name.value, lang),
                       goal=get_role_goal(role.name.value, lang),
                       team=get_team_name(role.team.value, lang))
        if role.team == Team.MAFIA:
            mafia_team = engine.get_mafia_team()
            teammates = [f"{ALL_ROLES[m.role].emoji} {m.username}" for m in mafia_team if m.user_id != p.user_id]
            if teammates:
                role_text += t("your_team", lang, teammates="\n".join(teammates))

        try:
            await bot.send_message(p.user_id, role_text, parse_mode="HTML",
                                   reply_markup=_chat_kb(chat_id))
        except Exception:
            pass  # Пользователь не начал диалог с ботом


async def _on_night_started(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    day = data["day"]
    lang = await get_lang(chat_id)
    
    # Нумерованный список — без эмодзи статуса
    alive = sorted(engine.alive_players_list(), key=lambda p: p.player_number)
    player_lines = "\n".join(f"{p.player_number}. {p.username}" for p in alive)
    
    # Роли по командам
    role_breakdown = _format_living_list(engine, lang)
    
    text = t("night_started", lang,
             day=day,
             players=player_lines,
             role_breakdown=role_breakdown,
             duration=settings.NIGHT_DURATION)
    
    await bot.send_message(chat_id, text, parse_mode="HTML")

    # Отправить ночные клавиатуры в ЛС
    from bot.handlers.game.night import send_night_actions
    await send_night_actions(bot, engine)


async def _on_night_ended(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    deaths: list[dict] = data["deaths"]
    afk_deaths: list[dict] = data.get("afk_deaths", [])
    vest_saves: list[int] = data.get("vest_saves", [])
    day = data["day"]
    lang = await get_lang(chat_id)

    all_deaths = deaths + afk_deaths

    if not all_deaths and not vest_saves:
        text = t("night_ended_safe", lang, day=day)
    else:
        lines = []
        # Боевые смерти (с перечислением всех убийц)
        for d in deaths:
            role = ALL_ROLES[d["role"]]
            p = engine.players.get(d["user_id"])
            name = p.username if p else "???"
            label = get_role_label(role.name.value, lang)
            reasons = d.get("reasons", [])
            if reasons:
                killers = ", ".join(t(f"kill_{r}", lang) for r in reasons)
                lines.append(t("death_line", lang,
                               name=name, emoji=role.emoji,
                               label=label, killers=killers))
            else:
                lines.append(t("death_line_no_reason", lang,
                               name=name, emoji=role.emoji, label=label))

        # AFK смерти
        if afk_deaths:
            afk_names = []
            for d in afk_deaths:
                role = ALL_ROLES[d["role"]]
                afk_names.append(f"{role.emoji} {get_role_label(role.name.value, lang)}")
            lines.append(t("afk_kicked", lang, roles=", ".join(afk_names)))

        # Щит
        if vest_saves:
            lines.append(t("vest_saved_chat", lang))

        text = t("night_ended_header", lang, day=day) + "\n".join(lines)

    await bot.send_message(chat_id, text, parse_mode="HTML")

    # DM уведомления о щите
    for uid in vest_saves:
        try:
            await bot.send_message(
                uid,
                t("vest_saved_dm", lang),
                parse_mode="HTML",
                reply_markup=_chat_kb(chat_id),
            )
        except Exception:
            pass


async def _on_day_started(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    day = data["day"]
    poisoned: list[int] = data.get("poisoned_deaths", [])
    alive = engine.alive_players_list()
    alive_sorted = sorted(alive, key=lambda p: p.player_number)
    lang = await get_lang(chat_id)

    text = t("day_started", lang, day=day)
    text += t("day_alive_count", lang, count=len(alive))

    # Пронумерованный список игроков
    for p in alive_sorted:
        display_name = p.username # Это теперь Full Name
        tag = f"<a href='tg://user?id={p.user_id}'>{display_name}</a>"
        text += f"{p.player_number}. {tag}\n"

    text += "\n"
    text += _format_living_list(engine, lang)

    if poisoned:
        names = [engine.players[uid].username for uid in poisoned if uid in engine.players]
        text += t("day_poison_header", lang) + "\n".join(f"💀 {n}" for n in names)
        for uid in poisoned:
            p = engine.players.get(uid)
            if p:
                label = get_role_label(p.role.value if hasattr(p.role, 'value') else p.role, lang)
                text += f" ({label})"

    text += t("day_discuss_time", lang, duration=settings.DAY_DURATION)
    await bot.send_message(chat_id, text, parse_mode="HTML")


    # Уведомляем тех, кто умер ночью, о возможности последнего слова
    for uid in engine.last_word_victims:
        try:
            await bot.send_message(uid, t("last_word_dm", lang),
                                   parse_mode="HTML", reply_markup=_chat_kb(chat_id))
        except Exception: pass

    from bot.config import settings as cfg


async def _on_vote_started(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    alive = engine.alive_players_list()
    lang = await get_lang(chat_id)
    text = t("vote_started", lang, duration=settings.VOTE_DURATION)
    await bot.send_message(chat_id, text, parse_mode="HTML")
    
    # Отправляем клавиатуры голосования всем живым в ЛС
    for p in alive:
        try:
            kb = day_vote_keyboard(alive, p.user_id, engine.game_id)
            kb_with_link = _with_chat_link(kb, chat_id)
            await bot.send_message(p.user_id, t("vote_dm", lang),
                                   reply_markup=kb_with_link, parse_mode="HTML")
        except Exception: pass


async def _on_trial_started(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    target_id = data["target_id"]
    p = engine.players.get(target_id)
    if not p: return
    lang = await get_lang(chat_id)

    text = t("trial_header", lang, name=p.username)
    await bot.send_message(chat_id, text, parse_mode="HTML")

    # Отправляем клавиатуру суда в чат
    from bot.keyboards.game_kb import trial_keyboard
    kb = trial_keyboard(engine.game_id)
    await bot.send_message(chat_id, t("trial_vote_prompt", lang),
                           reply_markup=kb, parse_mode="HTML")


async def _on_vote_ended(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    executed: Optional[int] = data.get("executed")
    was_trial = data.get("was_trial", False)
    lang = await get_lang(chat_id)
    
    if not was_trial:
        if not executed:
            await bot.send_message(chat_id, t("trial_no_victim", lang), parse_mode="HTML")
        else:
            p = engine.players.get(executed)
            if p:
                await bot.send_message(chat_id, t("trial_suspect", lang, name=p.username), parse_mode="HTML")
    else:
        # Результат суда
        likes = data.get("likes", 0)
        dislikes = data.get("dislikes", 0)
        
        if not executed:
            await bot.send_message(
                chat_id, 
                t("trial_acquitted", lang, likes=likes, dislikes=dislikes),
                parse_mode="HTML"
            )
        else:
            p = engine.players.get(executed)
            if p:
                role = ALL_ROLES[p.role]
                label = get_role_label(role.name.value, lang)
                if p.role == RoleName.JESTER:
                    await bot.send_message(
                        chat_id,
                        t("trial_jester_win", lang, name=p.username,
                          likes=likes, dislikes=dislikes),
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        chat_id,
                        t("trial_executed", lang, name=p.username,
                          likes=likes, dislikes=dislikes,
                          emoji=role.emoji, label=label),
                        parse_mode="HTML"
                    )


async def _on_game_finished(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    winner = data["winner"]
    snapshot = data["snapshot"]
    lang = await get_lang(chat_id)

    # ═══ 1. Очистка реестра ═══
    registry.remove(chat_id)

    # ═══ 2. Определяем победителей (только ЖИВЫЕ) ═══
    winners_list: list[dict] = []
    for p in snapshot:
        try:
            role = ALL_ROLES[RoleName(p["role"])]
            is_winner = (
                p["is_alive"] and (
                    (winner == "town"   and role.team == Team.TOWN) or
                    (winner == "mafia"  and role.team == Team.MAFIA) or
                    (winner == "maniac" and p["role"] == RoleName.MANIAC.value)
                )
            )
            if is_winner:
                winners_list.append(p)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error processing player snapshot entry: {e}")

    # ═══ 3. Сообщение в чат ═══
    try:
        winner_keys = {
            "town":   "game_over_town",
            "mafia":  "game_over_mafia",
            "maniac": "game_over_maniac",
            "nobody": "game_over_nobody",
        }
        text = t(winner_keys.get(winner, "game_over_nobody"), lang) + "\n"

        import random
        top_1 = random.choice(winners_list) if winners_list else None
        if top_1:
            top_tag = f"<a href='tg://user?id={top_1['user_id']}'>{top_1['username']}</a>"
            text += f"\n🌟 <b>Top 1:</b> {top_tag}!\n"

        text += t("game_over_players_header", lang)
        for p in snapshot:
            role = ALL_ROLES[RoleName(p["role"])]
            name_tag = f"<a href='tg://user?id={p['user_id']}'>{p['username']}</a>"
            label = get_role_label(role.name.value, lang)
            reward = f" (+{settings.WIN_REWARD_COINS} 🪙)" if any(w["user_id"] == p["user_id"] for w in winners_list) else ""
            if p["is_alive"]:
                text += f"✅ {name_tag} — {role.emoji} {label}{reward}\n"
            else:
                text += f"💀 {name_tag} — {role.emoji} {label}{reward}\n"

        end_msg = await bot.send_message(chat_id, text, parse_mode="HTML")
        try:
            await bot.pin_chat_message(chat_id, end_msg.message_id, disable_notification=True)
        except Exception:
            pass
        logging.getLogger(__name__).info(f"Game {engine.game_id}: sent game-end message, winner={winner}")
    except Exception as e:
        logging.getLogger(__name__).error(f"CRITICAL: Failed to send game end message to chat {chat_id}: {e}", exc_info=True)

    # ═══ 4. Пытаемся закрыть игру в БД ═══
    try:
        async with AsyncSessionLocal() as session:
            await finish_game(session, engine.game_id, winner, snapshot)
            await session.commit()
        logging.getLogger(__name__).info(f"Game {engine.game_id} marked finished in DB, winner={winner}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to finish game {engine.game_id} in DB: {e}", exc_info=True)

    # ═══ 5. DM каждому игроку ═══
    for p in snapshot:
        try:
            role = ALL_ROLES[RoleName(p["role"])]
            label = get_role_label(role.name.value, lang)
            is_win = any(w["user_id"] == p["user_id"] for w in winners_list)
            if is_win:
                dm_text = (
                    f"🏆 <b>{t('game_over_town', lang).split('!')[0] if winner == 'town' else t('game_over_mafia', lang).split('!')[0]}</b>\n"
                    f"{role.emoji} {label}\n"
                    f"+{settings.WIN_REWARD_COINS} 🪙"
                )
            else:
                dm_text = (
                    f"💀 <b>{t('game_over_nobody', lang)}</b>\n"
                    f"{role.emoji} {label}"
                )
            await bot.send_message(p["user_id"], dm_text, parse_mode="HTML")
        except Exception:
            pass

    # ═══ 6. Статистика игроков ═══
    try:
        async with AsyncSessionLocal() as session:
            for p in snapshot:
                try:
                    is_win = any(w["user_id"] == p["user_id"] for w in winners_list)
                    if is_win:
                        await update_balance(session, p["user_id"], delta_coins=settings.WIN_REWARD_COINS)
                    db_user = await get_or_create_user(session, p["user_id"])
                    if isinstance(db_user, tuple):
                        db_user = db_user[0]
                    db_user.games_played += 1
                    if is_win:
                        db_user.games_won += 1
                except Exception as e:
                    logging.getLogger(__name__).error(f"Error updating stats for user {p['user_id']}: {e}")
            await session.commit()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to update stats for game {engine.game_id}: {e}", exc_info=True)


async def _on_sergeant_promoted(bot: Bot, chat_id: int, data: dict):
    uid = data["user_id"]
    lang = await get_lang(chat_id)
    await bot.send_message(
        chat_id,
        t("sergeant_promoted_chat", lang, uid=uid),
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, t("sergeant_promoted_dm", lang),
                               parse_mode="HTML", reply_markup=_chat_kb(chat_id))
    except Exception:
        pass


async def _on_werewolf_activated(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    uid = data["user_id"]
    lang = await get_lang(chat_id)
    await bot.send_message(
        chat_id,
        t("werewolf_activated_chat", lang),
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, t("werewolf_activated_dm", lang),
                               parse_mode="HTML", reply_markup=_chat_kb(chat_id))
    except Exception:
        pass


async def _on_lobby_expired(bot: Bot, chat_id: int, engine: GameEngine, data: dict):
    count = data["count"]
    min_players = data["min"]
    lang = await get_lang(chat_id)
    await bot.send_message(chat_id, t("lobby_expired", lang, count=count, min=min_players))
    
    # Cleanup DB and Registry
    async with AsyncSessionLocal() as session:
        from bot.database.crud import finish_game
        await finish_game(session, engine.game_id, "expired", [])
        await session.commit()
    
    registry.remove(chat_id)


async def _on_jester_wins(bot: Bot, chat_id: int, data: dict, engine: GameEngine):
    uid = data["user_id"]
    # Начислить монеты Шуту
    async with AsyncSessionLocal() as session:
        await update_balance(session, uid, delta_coins=settings.WIN_REWARD_COINS)
        await log_transaction(session, uid, settings.WIN_REWARD_COINS, "coins", "jester_win")
        await session.commit()


# ─────────────────────────── HELPERS ─────────────────────────

def _format_player_list_night(engine: GameEngine, lang: str = "ru") -> str:
    """Форматирует список живых игроков с постоянными номерами."""
    alive = [p for p in engine.players.values() if p.is_alive]
    alive.sort(key=lambda x: x.player_number)
    
    mafia = [p for p in alive if p.role_obj.team == Team.MAFIA]
    town = [p for p in alive if p.role_obj.team == Team.TOWN]
    neutral = [p for p in alive if p.role_obj.team == Team.NEUTRAL]
    
    lines = [t("living_header", lang, count=len(alive))]
    
    for p in alive:
        display_name = p.username
        tag = f"<a href='tg://user?id={p.user_id}'>{display_name}</a>"
        lines.append(f"{p.player_number}. ✅ {tag}")
    
    lines.append(t("living_mafia", lang, count=len(mafia)))
    lines.append(t("living_town", lang, count=len(town)))
    lines.append(t("living_neutral", lang, count=len(neutral)))
    
    return "\n".join(lines)


async def _on_action_submitted(bot: Bot, chat_id: int, data: dict):
    role = data["role"]
    username = data["username"]
    action = data.get("action")
    lang = await get_lang(chat_id)
    
    if role == RoleName.COMMISSIONER:
        if action == "commissioner_shoot":
            text = t("action_flavor_commissioner_shoot", lang)
        else:
            text = t("action_flavor_commissioner_check", lang)
    else:
        flavor_map = {
            RoleName.MAFIA: "action_flavor_mafia",
            RoleName.DON: "action_flavor_don",
            RoleName.DOCTOR: "action_flavor_doctor",
            RoleName.PROSTITUTE: "action_flavor_prostitute",
            RoleName.MANIAC: "action_flavor_maniac",
            RoleName.NINJA: "action_flavor_ninja",
            RoleName.POISONER: "action_flavor_poisoner",
            RoleName.BARTENDER: "action_flavor_bartender",
            RoleName.LAWYER: "action_flavor_lawyer",
            RoleName.WITNESS: "action_flavor_witness",
            RoleName.ARMORER: "action_flavor_armorer",
            RoleName.NECROMANCER: "action_flavor_necromancer",
        }
        text = t(flavor_map.get(role, "action_flavor_default"), lang)
        
    await bot.send_message(chat_id, text)


async def _on_voted(bot: Bot, chat_id: int, data: dict):
    voter_id = data.get("voter_id")
    target_id = data.get("target_id")
    voter_tag = f"<a href='tg://user?id={voter_id}'>{data['voter']}</a>"
    lang = await get_lang(chat_id)
    
    if target_id == 0:  # воздержался
        await bot.send_message(chat_id, t("vote_skip", lang, voter=voter_tag), parse_mode="HTML")
    else:
        target_tag = f"<a href='tg://user?id={target_id}'>{data['target']}</a>"
        await bot.send_message(chat_id, t("vote_cast", lang, voter=voter_tag, target=target_tag), parse_mode="HTML")


async def _on_last_word_received(bot: Bot, chat_id: int, data: dict):
    username = data["username"]
    text = data["text"]
    lang = await get_lang(chat_id)
    await bot.send_message(chat_id, t("last_word_received", lang, name=username, text=text), parse_mode="HTML")


def _format_living_list(engine: GameEngine, lang: str = "ru") -> str:
    """
    Показывает только живые роли, сгруппированные по командам.
    Без имён игроков.
    """
    alive = [p for p in engine.players.values() if p.is_alive]

    town    = [p for p in alive if p.role_obj.team == Team.TOWN]
    mafia   = [p for p in alive if p.role_obj.team == Team.MAFIA]
    neutral = [p for p in alive if p.role_obj.team == Team.NEUTRAL]

    from collections import Counter

    def role_lines(players: list) -> list[str]:
        counts = Counter(p.role_obj for p in players)
        lines = []
        for role, cnt in counts.items():
            label = get_role_label(role.name.value, lang)
            suffix = f" ×{cnt}" if cnt > 1 else ""
            lines.append(f"  {role.emoji} <i>{label}</i>{suffix}")
        return lines

    sections: list[str] = []

    if town:
        header = f"☀️ <b>{t('team_town', lang)} ({len(town)}):</b>" if lang == "ru" else f"☀️ <b>{t('team_town', lang)} ({len(town)}):</b>"
        lines = [header]
        lines += role_lines(town)
        sections.append("\n".join(lines))

    if mafia:
        header = f"🌑 <b>{t('team_mafia', lang)} ({len(mafia)}):</b>"
        lines = [header]
        lines += role_lines(mafia)
        sections.append("\n".join(lines))

    if neutral:
        header = f"🎭 <b>{t('team_neutral', lang)} ({len(neutral)}):</b>"
        lines = [header]
        lines += role_lines(neutral)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
