"""
Member event handlers:
  - Silently delete "user left the group" service messages.
  - Greet new members with a clickable profile link and a warm welcome message.
"""
from __future__ import annotations

import random
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter

logger = logging.getLogger(__name__)
router = Router()

# ─── Greetings pool ──────────────────────────────────────────────

WELCOME_MESSAGES = [
    "🎉 Добро пожаловать, {name}! Рады тебя видеть в нашем городке. Здесь не всё так мирно, как кажется... 😈",
    "👋 {name} появился в городе! Надеемся, твоя роль окажется добродетельной... или нет? 😏",
    "🔔 Внимание! {name} вступил(а) в нашу компанию. Добро пожаловать — берегись мафии! 🕵️",
    "🌟 {name}, ты как раз вовремя! Следующая игра ждёт своего часа. Добро пожаловать! 🎮",
    "🃏 {name} присоединился к игре! Удачи тебе — она тебе понадобится... 🍀",
    "🏘️ Городок рад приветствовать {name}! Улыбайся — маньяк рядом. 🔨",
    "🎭 {name} прибыл(а)! Твоя роль будет известна в следующей партии. Добро пожаловать! 🎲",
]


# ─── New member: Welcome ──────────────────────────────────────────

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_member_join(update: ChatMemberUpdated, bot: Bot):
    """Приветствуем нового участника с кликабельным именем."""
    user = update.new_chat_member.user
    if user.is_bot:
        return

    name_tag = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    text = random.choice(WELCOME_MESSAGES).format(name=name_tag)

    try:
        await bot.send_message(
            update.chat.id,
            text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed to send welcome to chat {update.chat.id}: {e}")


# ─── Left member: Delete service message ─────────────────────────

@router.message(F.left_chat_member)
async def on_member_leave(message: Message):
    """Удаляем служебное сообщение 'участник покинул группу'."""
    try:
        await message.delete()
    except Exception:
        pass
