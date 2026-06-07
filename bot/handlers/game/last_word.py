"""
Last Word handler — перехватывает текстовые сообщения в ЛС
и транслирует их в чат игры как "Последнее слово".
"""
from __future__ import annotations

from aiogram import F, Router, types
from bot.game import registry

router = Router()

@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def handle_last_word(message: types.Message):
    """Принимает текст в ЛС и отправляет в игру, если игрок имеет право на последнее слово."""
    user_id = message.from_user.id
    engine = registry.get_by_user_id(user_id)
    
    if not engine:
        return # Игрок не в игре

    # Пытаемся отправить как последнее слово
    success = await engine.submit_last_word(user_id, message.text)
    if success:
        await message.answer("📢 Ваше последнее слово отправлено в чат игры.")
    else:
        # Если не успех, значит либо фаза не та, либо он не жертва этой ночи.
        # Просто игнорируем или можно добавить лог.
        pass
