"""
Middleware:
1. WhitelistMiddleware — проверяет, что чат в белом списке (для групп)
2. BanCheckMiddleware — проверяет, не забанен ли пользователь
3. GameChatGuardMiddleware — удаляет сообщения во время игры
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.database.crud import get_chat, get_user
from bot.database.engine import AsyncSessionLocal

logger = logging.getLogger(__name__)


class WhitelistMiddleware(BaseMiddleware):
    """Разрешает команды только из белого списка чатов (для групп)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # ЛС — всегда разрешаем
        if event.chat.type == "private":
            return await handler(event, data)

        chat_id = event.chat.id
        async with AsyncSessionLocal() as session:
            chat = await get_chat(session, chat_id)
            if not chat or not chat.is_active:
                return  # Молча игнорируем

        return await handler(event, data)


class BanCheckMiddleware(BaseMiddleware):
    """Блокирует забаненных пользователей."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            db_user = await get_user(session, user.id)
            if db_user and db_user.is_banned:
                await event.answer("🚫 Вы заблокированы.")
                return

        return await handler(event, data)


class GameChatGuardMiddleware(BaseMiddleware):
    """
    Удаляет сообщения в чате во время активной игры:
    
    - Ночь:       удаляются ВСЕ сообщения (включая админов без !)
    - День/Суд:   писать могут только ЖИВЫЕ игроки
    - Лобби:      писать могут все
    - Вне игры:   без ограничений
    
    Админы могут обойти фильтр, начав сообщение с «!»
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        # Работаем только в группах
        if event.chat.type == "private":
            return await handler(event, data)

        # Пропускаем команды бота (начинаются с /)
        if event.text and event.text.startswith("/"):
            return await handler(event, data)

        from bot.game import registry

        chat_id = event.chat.id
        engine = registry.get(chat_id)

        # Нет активной игры — пропускаем
        if not engine:
            return await handler(event, data)

        phase = engine.phase

        # Лобби и финиш — без ограничений
        if phase in ("lobby", "finished"):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)

        # ── Проверка «!» от админа ──
        msg_text = event.text or event.caption or ""
        if msg_text.startswith("!"):
            from bot.utils.permissions import is_admin
            bot = data.get("bot")
            if bot and await is_admin(bot, chat_id, user_id):
                return await handler(event, data)

        # ── Ночь: удаляем ВСЁ ──
        if phase == "night":
            try:
                await event.delete()
            except Exception:
                pass
            return  # Не передаём дальше

        # ── День / Голосование / Суд: только живые игроки ──
        if phase in ("day", "vote", "trial"):
            player = engine.players.get(user_id)
            if player and player.is_alive:
                return await handler(event, data)

            # Не игрок или мёртв — удаляем
            try:
                await event.delete()
            except Exception:
                pass
            return

        # Неизвестная фаза — пропускаем
        return await handler(event, data)
