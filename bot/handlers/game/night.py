"""
Night phase handlers — отправляет ночные клавиатуры в ЛС,
обрабатывает callback-ответы от игроков.
"""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.game.engine import GameEngine
from bot.game.roles import ALL_ROLES, APPEARS_CIVILIAN, RoleName, Team
from bot.game import registry
from bot.keyboards.game_kb import (
    commissioner_action_keyboard, mafia_vote_keyboard,
    players_target_keyboard, back_to_chat_button,
)
from bot.i18n import t, get_lang, get_role_label

import logging
logger = logging.getLogger(__name__)

router = Router()


def _with_chat_link(kb, chat_id: int, game_id: int):
    """Добавляет кнопку 'Перейти в чат' снизу к любой существующей клавиатуре."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    engine = registry.get(chat_id)
    msg_id = (engine.lobby_message_id or 1) if engine else 1
    builder = InlineKeyboardBuilder.from_markup(kb)
    builder.row(InlineKeyboardButton(text="💬 Перейти в чат",
                                     url=f"https://t.me/c/{str(chat_id).replace('-100', '')}/{msg_id}"))
    return builder.as_markup()


async def send_night_actions(bot: Bot, engine: GameEngine) -> None:
    """Рассылка ночных клавиатур всем живым игрокам с ночными действиями."""
    alive = engine.alive_players_list()
    mafia_alive = [p for p in alive if p.role_obj.team == Team.MAFIA]
    chat_id = engine.chat_id
    gid = engine.game_id
    lang = await get_lang(chat_id)

    for p in alive:
        role = p.role_obj
        try:
            if not role.has_night_action:
                # Мирный без хода — просто уведомление
                if p.role == RoleName.SERGEANT:
                    # Сержант видит результаты проверок и самого Комиссара
                    comm = next((s for s in alive if s.role == RoleName.COMMISSIONER), None)
                    comm_info = f"\n🔫 <b>{get_role_label('commissioner', lang)}:</b> {comm.username}" if comm else ""
                    if engine.commissioner_results:
                        await bot.send_message(
                            p.user_id,
                            f"🪖 <b>{get_role_label('sergeant', lang)}</b>{comm_info}\n" +
                            "\n".join(engine.commissioner_results),
                            reply_markup=back_to_chat_button(chat_id, gid),
                            parse_mode="HTML"
                        )
                    else:
                        await bot.send_message(p.user_id, f"🌙 <b>{get_role_label('sergeant', lang)}</b>{comm_info}",
                                               reply_markup=back_to_chat_button(chat_id, gid), parse_mode="HTML")
                else:
                    await bot.send_message(p.user_id, "🌙 ...",
                                           reply_markup=back_to_chat_button(chat_id, gid))
                continue

            # Роль-специфичные клавиатуры
            match p.role:
                case RoleName.DOCTOR:
                    # Доктор может лечить себя только 1 раз
                    exclude_self = [p.user_id] if p.doctor_healed_self else []
                    kb = players_target_keyboard(alive, "doctor_save", gid, exclude_ids=exclude_self)
                    await bot.send_message(p.user_id, t("night_dm_doctor", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.COMMISSIONER:
                    sergeant = next((s for s in alive if s.role == RoleName.SERGEANT), None)
                    extra = f"\n🤝 <b>{get_role_label('sergeant', lang)}:</b> {sergeant.username}" if sergeant else ""
                    await bot.send_message(p.user_id, t("night_dm_commissioner", lang) + extra,
                                           reply_markup=_with_chat_link(commissioner_action_keyboard(gid), chat_id, gid), parse_mode="HTML")

                case RoleName.PROSTITUTE:
                    kb = players_target_keyboard(alive, "prostitute_block", gid, exclude_ids=[p.user_id])
                    await bot.send_message(p.user_id, t("night_dm_prostitute", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.JOURNALIST:
                    kb = players_target_keyboard(alive, "journalist_p1", gid, exclude_ids=[p.user_id])
                    await bot.send_message(p.user_id, t("night_dm_journalist", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.WITNESS:
                    kb = players_target_keyboard(alive, "witness_watch", gid, exclude_ids=[p.user_id])
                    await bot.send_message(p.user_id, t("night_dm_witness", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.ARMORER:
                    if p.armorer_cooldown == 0:
                        kb = players_target_keyboard(alive, "armorer_action", gid)
                        await bot.send_message(p.user_id, t("night_dm_armorer", lang),
                                               reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")
                    else:
                        await bot.send_message(p.user_id,
                                               t("night_dm_armorer_cooldown", lang, n=p.armorer_cooldown),
                                               reply_markup=back_to_chat_button(chat_id, gid))

                case RoleName.NECROMANCER:
                    if p.necro_cooldown == 0 and engine.dead_roles:
                        dead_players = [dp for dp in engine.players.values() if not dp.is_alive]
                        kb = players_target_keyboard(dead_players, "necromancer_revive", gid)
                        await bot.send_message(p.user_id, t("night_dm_necromancer", lang),
                                               reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")
                    else:
                        await bot.send_message(p.user_id,
                                               t("night_dm_necromancer_cooldown", lang, n=p.necro_cooldown),
                                               reply_markup=back_to_chat_button(chat_id, gid))

                case RoleName.MAFIA | RoleName.DON:
                    # Мафия голосует за жертву
                    kb = mafia_vote_keyboard(alive, gid)
                    
                    teammates = [f" {ALL_ROLES[m.role].emoji} <b>{m.username}</b>"
                                 for m in mafia_alive if m.user_id != p.user_id]
                    team_info = "\n🤝 <b>" + t("your_team", lang, teammates="\n".join(teammates)).strip() if teammates else ""
                    
                    label = get_role_label(p.role.value, lang)
                    don_note = "\n\n👑 <i>x2</i>" if p.role == RoleName.DON else ""
                    
                    await bot.send_message(
                        p.user_id,
                        f"🔪 <b>{label}</b>\n{team_info}{don_note}",
                        reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML"
                    )
                    logger.info(f"Sent night action to {p.username} ({p.role})")

                case RoleName.NINJA:
                    alive_non_mafia = [p2 for p2 in alive if p2.role_obj.team != Team.MAFIA]
                    kb = players_target_keyboard(alive_non_mafia, "ninja_kill", gid)
                    await bot.send_message(p.user_id, t("night_dm_ninja", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")
                    logger.info(f"Sent night action to {p.username} ({p.role})")

                case RoleName.MANIAC:
                    kb = players_target_keyboard(alive, "maniac_kill", gid, exclude_ids=[p.user_id])
                    await bot.send_message(p.user_id, t("night_dm_maniac", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.POISONER:
                    kb = players_target_keyboard(alive, "poisoner_poison", gid, exclude_ids=[p.user_id])
                    await bot.send_message(p.user_id, t("night_dm_poisoner", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

                case RoleName.BARTENDER:
                    if p.bartender_cooldown == 0:
                        kb = players_target_keyboard(alive, "bartender_steal", gid, exclude_ids=[p.user_id])
                        await bot.send_message(p.user_id, t("night_dm_bartender", lang),
                                               reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")
                    else:
                        await bot.send_message(p.user_id,
                                               t("night_dm_bartender_cooldown", lang, n=p.bartender_cooldown),
                                               reply_markup=back_to_chat_button(chat_id, gid))

                case RoleName.LAWYER:
                    alive_mafia = [p2 for p2 in alive if p2.role_obj.team == Team.MAFIA and p2.user_id != p.user_id]
                    kb = players_target_keyboard(alive_mafia, "lawyer_protect", gid)
                    await bot.send_message(p.user_id, t("night_dm_lawyer", lang),
                                           reply_markup=_with_chat_link(kb, chat_id, gid), parse_mode="HTML")

            logger.info(f"Sent night action to {p.username} ({p.role})")

        except Exception as e:
            logger.error(f"Failed to send night action to {p.user_id}: {e}")
            pass


# ─────────────────── Night Action Callbacks ──────────────────────

@router.callback_query(F.data.startswith("doctor_save:"))
async def cb_doctor_save(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return await callback.answer("❌", show_alert=True)
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "doctor_save", target_id)
    name = _get_name(engine, target_id)
    await callback.answer(f"✅ {name}" if name else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("com_choose:"))
async def cb_com_choose(callback: CallbackQuery, bot: Bot):
    """Комиссар выбирает: проверить или стрелять."""
    _, gid, action = callback.data.split(":")
    gid = int(gid)
    engine = registry.get_by_game_id(gid)
    if not engine:
        return await callback.answer("❌", show_alert=True)
    lang = await get_lang(engine.chat_id)
    alive = engine.alive_players_list()
    uid = callback.from_user.id
    if action == "check":
        kb = players_target_keyboard(alive, "commissioner_check", gid, exclude_ids=[uid])
        await callback.message.edit_text(t("night_dm_commissioner_check", lang), reply_markup=kb, parse_mode="HTML")
    else:
        kb = players_target_keyboard(alive, "commissioner_shoot", gid, exclude_ids=[uid])
        await callback.message.edit_text(t("night_dm_commissioner_shoot", lang), reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("commissioner_check:"))
async def cb_commissioner_check(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return await callback.answer("❌", show_alert=True)
    lang = await get_lang(engine.chat_id)
    target_id = int(target)
    engine.submit_night_action(callback.from_user.id, "commissioner_check", target_id)
    result = engine.get_commissioner_result(target_id)
    name = _get_name(engine, target_id)
    engine.commissioner_results.append(f"🔍 {name}: {result}")
    
    # Check team directly — string matching breaks for "Дон Мафии", "Ниндзя", etc.
    target_p = engine.players.get(target_id)
    is_mafia = (
        target_p is not None
        and not target_p.has_docs
        and target_p.role not in APPEARS_CIVILIAN
        and target_p.role_obj.team == Team.MAFIA
    )
    if is_mafia:
        msg_text = t("night_dm_commissioner_result_mafia", lang, name=name)
    else:
        msg_text = t("night_dm_commissioner_result_town", lang, name=name)
    
    # Результат обоим (Кому и Сержанту)
    police_ids = engine.get_police_team_uids()
    for uid in police_ids:
        try:
            if uid == callback.from_user.id:
                await callback.message.edit_text(msg_text, parse_mode="HTML")
            else:
                await callback.bot.send_message(uid, f"📡 {msg_text}", parse_mode="HTML")
        except Exception:
            pass
    
    await callback.answer("✅")


@router.callback_query(F.data.startswith("commissioner_shoot:"))
async def cb_commissioner_shoot(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return await callback.answer("❌", show_alert=True)
    target_id = int(target)
    engine.submit_night_action(callback.from_user.id, "commissioner_shoot", target_id)
    name = _get_name(engine, target_id)
    await callback.answer(f"🔫 {name}!")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("journalist_p1:"))
async def cb_journalist_p1(callback: CallbackQuery):
    _, gid, p1 = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine: return
    lang = await get_lang(engine.chat_id)
    
    if p1 == "skip":
        engine.submit_night_action(callback.from_user.id, "journalist_compare", None)
        await callback.answer(t("action_skip", lang))
        await callback.message.edit_text("📰 ⏭")
        return

    p1_id = int(p1)
    name1 = _get_name(engine, p1_id)
    alive = engine.alive_players_list()
    
    # Создаем клавиатуру для второго игрока. 
    # В action запекаем id первого игрока через черточку.
    kb = players_target_keyboard(alive, f"journalist_p2_{p1_id}", int(gid), 
                                 exclude_ids=[callback.from_user.id, p1_id])
    
    await callback.message.edit_text(t("night_dm_journalist_p2", lang), 
                                   reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("journalist_p2_"))
async def cb_journalist_p2(callback: CallbackQuery):
    # Дата формата: journalist_p2_{p1}:{gid}:{p2}
    parts = callback.data.split(":")
    prefix = parts[0] # journalist_p2_{p1}
    gid = int(parts[1])
    p2 = parts[2]
    
    p1_id = int(prefix.split("_")[-1])
    engine = registry.get_by_game_id(gid)
    if not engine: return
    lang = await get_lang(engine.chat_id)

    if p2 == "skip":
        engine.submit_night_action(callback.from_user.id, "journalist_compare", None)
        await callback.answer(t("action_skip", lang))
        await callback.message.edit_text("📰 ⏭")
        return

    p2_id = int(p2)
    engine.submit_night_action(callback.from_user.id, "journalist_compare", p1_id, p2_id)
    
    res = engine.get_journalist_result(p1_id, p2_id)
    name1 = _get_name(engine, p1_id)
    name2 = _get_name(engine, p2_id)
    
    # Determine same or different team
    is_same = "одн" in res.lower() or "same" in res.lower()
    if is_same:
        text = t("night_dm_journalist_result_same", lang, name1=name1, name2=name2)
    else:
        text = t("night_dm_journalist_result_diff", lang, name1=name1, name2=name2)
    
    await callback.message.edit_text(text, reply_markup=back_to_chat_button(engine.chat_id, engine.game_id), parse_mode="HTML")
    await callback.answer("✅")

@router.callback_query(F.data.startswith("prostitute_block:"))
async def cb_prostitute(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "prostitute_block", target_id)
    await callback.answer(f"✅ {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("mafia_kill:"))
async def cb_mafia_kill(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "mafia_kill", target_id)
    await callback.answer(f"✅ {_get_name(engine, target_id)}" if target_id else "⏭ Пропустить")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("ninja_kill:"))
async def cb_ninja_kill(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = int(target)
    engine.submit_night_action(callback.from_user.id, "ninja_kill", target_id)
    await callback.answer(f"🥷 {_get_name(engine, target_id)}")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("maniac_kill:"))
async def cb_maniac_kill(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "maniac_kill", target_id)
    await callback.answer(f"✅ {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("poisoner_poison:"))
async def cb_poisoner(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "poisoner_poison", target_id)
    await callback.answer(f"☠️ {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("lawyer_protect:"))
async def cb_lawyer(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "lawyer_protect", target_id)
    await callback.answer(f"⚖️ {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("witness_watch:"))
async def cb_witness(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    engine.submit_night_action(callback.from_user.id, "witness_watch", target_id)
    await callback.answer(f"👀 {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("armorer_action:"))
async def cb_armorer(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    if target_id:
        actor = engine.players.get(callback.from_user.id)
        if actor:
            # Ограничение: себе только раз за игру
            if target_id == callback.from_user.id and actor.armorer_used_self:
                await callback.answer("❌", show_alert=True)
                return
            if target_id == callback.from_user.id:
                actor.armorer_used_self = True
            actor.armorer_cooldown = 3
    engine.submit_night_action(callback.from_user.id, "armorer_action", target_id)
    await callback.answer(f"🛡 {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("necromancer_revive:"))
async def cb_necromancer(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    if target_id:
        actor = engine.players.get(callback.from_user.id)
        if actor:
            actor.necro_cooldown = 3
    engine.submit_night_action(callback.from_user.id, "necromancer_revive", target_id)
    await callback.answer(f"💀 {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.callback_query(F.data.startswith("bartender_steal:"))
async def cb_bartender(callback: CallbackQuery):
    _, gid, target = callback.data.split(":")
    engine = registry.get_by_game_id(int(gid))
    if not engine:
        return
    target_id = None if target == "skip" else int(target)
    if target_id:
        actor = engine.players.get(callback.from_user.id)
        if actor:
            actor.bartender_cooldown = 2
    engine.submit_night_action(callback.from_user.id, "bartender_steal", target_id)
    await callback.answer(f"🍺 {_get_name(engine, target_id)}" if target_id else "⏭")
    await callback.message.edit_reply_markup(reply_markup=back_to_chat_button(engine.chat_id, engine.game_id))


@router.message(F.chat.type == "private")
async def night_chat_relay(message: Message, bot: Bot):
    """Релей сообщений между членами команд ночью."""
    if not message.text or message.text.startswith("/"):
        return

    engine = registry.get_by_user_id(message.from_user.id)
    if not engine or engine.phase != "night":
        return

    player = engine.players.get(message.from_user.id)
    if not player or not player.is_alive:
        return

    mafia_ids = engine.get_mafia_team_uids()
    police_ids = engine.get_police_team_uids()

    text = f"🗣 <b>{player.display()}</b>: {message.text}"
    target_ids = []

    if message.from_user.id in mafia_ids:
        target_ids = [uid for uid in mafia_ids if uid != message.from_user.id]
    elif message.from_user.id in police_ids:
        target_ids = [uid for uid in police_ids if uid != message.from_user.id]

    if not target_ids:
        return

    for uid in target_ids:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
        except Exception:
            pass


# ─────────────────── Utilities ───────────────────────────────────

def _get_name(engine: GameEngine | None, user_id: int | None) -> str:
    if not engine or not user_id:
        return "—"
    p = engine.players.get(user_id)
    return p.username if p else str(user_id)
