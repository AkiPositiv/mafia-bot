"""
Moderation handlers: /mute, /unmute, /warn, /unwarn, /ban, /unban, /call.

All commands:
  - Require admin privileges
  - Delete the command message
  - Send a public notification with clickable admin & target profile links
  - Accept optional reason at the end of the command (after the time arg for /mute)

Usage:
  /mute [minutes] [reason]    — reply required
  /unmute                     — reply or user_id
  /warn [reason]              — reply required
  /unwarn                     — reply or user_id
  /ban [reason]               — reply required
  /unban                      — reply or user_id
  /call                       — admin only
"""
from __future__ import annotations

import logging
import time

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions, CallbackQuery

from bot.database.crud import get_user
from bot.database.engine import AsyncSessionLocal
from bot.utils.permissions import is_admin
from bot.i18n import t, get_lang, set_lang

logger = logging.getLogger(__name__)
router = Router()


def _tag(user_id: int, name: str) -> str:
    """HTML-ссылка на профиль пользователя."""
    return f"<a href='tg://user?id={user_id}'>{name}</a>"


def _parse_reason(args: list[str], start: int) -> str:
    """Извлекает причину из args начиная с позиции start."""
    raw = " ".join(args[start:]).strip()
    return raw if raw else None


DEFAULT_REASONS = {
    "mute":  "нарушение правил",
    "warn":  "нарушение правил",
    "ban":   "нарушение правил",
}


# ─────────────────────── /mute ───────────────────────────────────

@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot):
    """/mute [minutes] [reason]"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя.")
        return

    args = message.text.split()
    minutes = 5
    reason_start = 1  # args[1] might be minutes

    if len(args) > 1:
        try:
            minutes = int(args[1])
            reason_start = 2  # reason starts after minutes
        except ValueError:
            reason_start = 1  # no minutes given, reason starts at index 1

    reason = _parse_reason(args, reason_start) or DEFAULT_REASONS["mute"]
    until_date = int(time.time() + minutes * 60)
    target = message.reply_to_message.from_user

    try:
        await message.chat.restrict(
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
    except Exception as e:
        logger.error(f"Failed to mute user: {e}")
        await message.answer("❌ Не удалось ограничить права. Возможно, у бота нет прав или пользователь — админ.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target.id, target.full_name)
    await message.answer(
        f"🔇 {admin_tag} замутил {target_tag} на <b>{minutes} мин.</b>\n"
        f"📋 Причина: {reason}",
        parse_mode="HTML"
    )


# ─────────────────────── /unmute ─────────────────────────────────

@router.message(Command("unmute"))
async def cmd_unmute(message: Message, bot: Bot):
    """/unmute — reply or user_id"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    target_id: int | None = None
    target_name = "пользователь"
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        args = message.text.split()
        if len(args) > 1:
            try:
                target_id = int(args[1])
            except ValueError:
                pass

    if not target_id:
        await message.answer("❌ Укажите ID или ответьте на сообщение пользователя.")
        return

    try:
        await message.chat.restrict(
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True,
                can_send_documents=True, can_send_photos=True,
                can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_change_info=False, can_invite_users=True, can_pin_messages=False
            )
        )
    except Exception as e:
        logger.error(f"Failed to unmute: {e}")
        await message.answer("❌ Не удалось снять ограничения.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target_id, target_name)
    await message.answer(f"🔊 {admin_tag} снял мут с {target_tag}.", parse_mode="HTML")


# ─────────────────────── /warn ───────────────────────────────────

@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot):
    """/warn [reason]"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя.")
        return

    target = message.reply_to_message.from_user
    if target.id == message.bot.id:
        await message.answer("❌ Нельзя варнить бота.")
        return

    args = message.text.split()
    reason = _parse_reason(args, 1) or DEFAULT_REASONS["warn"]

    async with AsyncSessionLocal() as session:
        user = await get_user(session, target.id)
        if not user:
            from bot.database.crud import get_or_create_user
            user, _ = await get_or_create_user(session, target.id, target.username, target.full_name)
        user.warn_count += 1
        current_warns = user.warn_count
        await session.commit()

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target.id, target.full_name)

    if current_warns >= 3:
        try:
            await message.chat.ban(user_id=target.id)
            async with AsyncSessionLocal() as session:
                user = await get_user(session, target.id)
                if user:
                    user.is_banned = True
                    user.warn_count = 0
                    await session.commit()
            await message.answer(
                f"🚫 {admin_tag} выдал варн #{current_warns} пользователю {target_tag}.\n"
                f"📋 Причина: {reason}\n"
                f"⛔ 3/3 варна — пользователь <b>заблокирован</b>.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to ban after 3 warns: {e}")
            await message.answer(
                f"⚠️ {admin_tag} выдал #{current_warns}/3 варнов {target_tag}, но не удалось забанить.",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            f"⚠️ {admin_tag} выдал варн {target_tag} ({current_warns}/3).\n"
            f"📋 Причина: {reason}",
            parse_mode="HTML"
        )


# ─────────────────────── /unwarn ─────────────────────────────────

@router.message(Command("unwarn"))
async def cmd_unwarn(message: Message, bot: Bot):
    """/unwarn — reply or user_id"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    target_id: int | None = None
    target_name = "пользователь"
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        args = message.text.split()
        if len(args) > 1:
            try:
                target_id = int(args[1])
            except ValueError:
                pass

    if not target_id:
        await message.answer("❌ Укажите ID или ответьте на сообщение.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user(session, target_id)
        if user:
            user.warn_count = 0
            await session.commit()
        else:
            await message.answer("❌ Пользователь не найден в базе.")
            return

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target_id, target_name)
    await message.answer(f"✅ {admin_tag} сбросил варны у {target_tag}.", parse_mode="HTML")


# ─────────────────────── /ban ────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    """/ban [reason] — reply required"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя.")
        return

    target = message.reply_to_message.from_user
    args = message.text.split()
    reason = _parse_reason(args, 1) or DEFAULT_REASONS["ban"]

    async with AsyncSessionLocal() as session:
        user = await get_user(session, target.id)
        if user:
            user.is_banned = True
            await session.commit()

    try:
        await message.chat.ban(user_id=target.id)
    except Exception as e:
        logger.error(f"Failed to ban: {e}")
        await message.answer("❌ Не удалось забанить пользователя.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target.id, target.full_name)
    await message.answer(
        f"🚫 {admin_tag} заблокировал {target_tag} <b>навсегда</b>.\n"
        f"📋 Причина: {reason}",
        parse_mode="HTML"
    )


# ─────────────────────── /unban ──────────────────────────────────

@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    """/unban — reply or user_id"""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    target_id: int | None = None
    target_name = "пользователь"
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        args = message.text.split()
        if len(args) > 1:
            try:
                target_id = int(args[1])
            except ValueError:
                pass

    if not target_id:
        await message.answer("❌ Укажите ID или ответьте на сообщение.")
        return

    async with AsyncSessionLocal() as session:
        from bot.database.crud import set_ban
        await set_ban(session, target_id, False)
        await session.commit()

    try:
        await message.chat.unban(user_id=target_id)
    except Exception as e:
        logger.error(f"Failed to unban in chat: {e}")

    try:
        await message.delete()
    except Exception:
        pass

    admin_tag = _tag(message.from_user.id, message.from_user.full_name)
    target_tag = _tag(target_id, target_name)
    await message.answer(f"✅ {admin_tag} разбанил {target_tag}.", parse_mode="HTML")


# ─────────────────────── /call ───────────────────────────────────

# Пул уникальных эмодзи для тегов (200+ штук)
_CALL_EMOJI = [
    "🍎","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍒","🍑","🥭","🍍","🥝","🍅","🥑",
    "🌽","🥕","🧅","🧄","🥔","🍆","🌶️","🥒","🥬","🥦","🫑","🍄","🥜","🌰","🫘",
    "🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🐯","🦁","🐮","🐷","🐸","🐵",
    "🐔","🐧","🐦","🐤","🦆","🦅","🦉","🦇","🐺","🐗","🐴","🦄","🐝","🪲","🦋",
    "🐌","🐛","🐜","🐞","🦗","🕷️","🦂","🐢","🐍","🦎","🐙","🦑","🦐","🦀","🐡",
    "🐠","🐟","🐬","🐳","🐋","🦈","🐊","🐅","🐆","🦓","🦍","🦧","🐘","🦛","🦏",
    "🏳️","🏴","🚩","🇦🇷","🇧🇷","🇨🇦","🇨🇳","🇫🇷","🇩🇪","🇮🇳","🇮🇹","🇯🇵","🇰🇷","🇲🇽","🇷🇺",
    "🇬🇧","🇺🇸","🇪🇸","🇹🇷","🇦🇺","🇳🇱","🇸🇪","🇳🇴","🇩🇰","🇫🇮","🇵🇱","🇺🇦","🇰🇿","🇬🇪","🇦🇿",
    "⚽","🏀","🏈","⚾","🎾","🏐","🎱","🏓","🏸","🥊","🎯","⛳","🏋️","🤺","🎿",
    "🎸","🎹","🥁","🎺","🎷","🪗","🎻","🎤","🎧","🎬","🎨","🎭","🎪","🎰","🎲",
    "🚗","🚕","🚙","🏎️","🚓","🚑","🚒","🚐","🛻","🚚","🚜","🏍️","🛵","🚲","🛴",
    "✈️","🚀","🛸","🚁","⛵","🚢","⚓","🗿","🗽","🏰","🗼","⛩️","🕌","⛪","🏛️",
    "💎","🔮","🪩","🧲","🔭","🧪","🧬","💊","🩺","🛡️","⚔️","🔱","🪬","📿","🧿",
    "🌸","🌺","🌻","🌹","🌷","🪻","💐","🌼","🍀","🌿","🌵","🎄","🎋","🎍","🍁",
]

import random as _random


@router.message(Command("call"))
async def cmd_call(message: Message, bot: Bot):
    """/call — позвать только тех, кто сейчас в чате, скрытые эмодзи-теги."""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    chat_id = message.chat.id
    from sqlalchemy import select
    from bot.database.models import GamePlayer, User, Game

    async with AsyncSessionLocal() as session:
        stmt = (
            select(User.id, User.full_name)
            .join(GamePlayer, User.id == GamePlayer.user_id)
            .join(Game, GamePlayer.game_id == Game.id)
            .where(Game.chat_id == chat_id)
            .distinct()
        )
        result = await session.execute(stmt)
        users = result.all()

    if not users:
        await message.answer("🕵️ В этом чате ещё никто не играл.")
        return

    # Фильтруем: оставляем только тех, кто сейчас в чате
    present: list[tuple[int, str]] = []
    for uid, name in users:
        try:
            member = await bot.get_chat_member(chat_id, uid)
            if member.status in ("member", "administrator", "creator", "restricted"):
                present.append((uid, name))
        except Exception:
            pass  # пользователь не найден / бот не может проверить

    if not present:
        await message.answer("🕵️ Никто из игроков сейчас не в чате.")
        return

    # Удаляем команду
    try:
        await message.delete()
    except Exception:
        pass

    # Перемешиваем эмодзи и назначаем уникальный каждому
    pool = list(_CALL_EMOJI)
    _random.shuffle(pool)

    tags = []
    for i, (uid, _name) in enumerate(present):
        emoji = pool[i % len(pool)]
        tags.append(f"<a href='tg://user?id={uid}'>{emoji}</a>")

    # Telegram тегает максимум ~5 за одно сообщение
    chunk_size = 5
    header = "🔔 <b>Общий сбор!</b>\n\n"
    for i in range(0, len(tags), chunk_size):
        chunk = tags[i:i + chunk_size]
        msg_text = (header if i == 0 else "") + " ".join(chunk)
        await message.answer(msg_text, parse_mode="HTML")


# ─────────────────────── /lang ───────────────────────────────────

@router.message(Command("lang"))
async def cmd_lang(message: Message, bot: Bot):
    """/lang — выбрать язык чата."""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set_lang:uz"),
    )

    await message.answer(
        "🌐 <b>Выберите язык / Tilni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(callback: CallbackQuery):
    """Callback: set_lang:ru / set_lang:uz"""
    lang = callback.data.split(":")[1]
    if lang not in ("ru", "uz"):
        await callback.answer("❌")
        return

    chat_id = callback.message.chat.id
    await set_lang(chat_id, lang)

    response = t("lang_set", lang)
    await callback.message.edit_text(response, reply_markup=None, parse_mode="HTML")
    await callback.answer()
