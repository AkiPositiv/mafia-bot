from aiogram import Bot
from bot.config import settings

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь админом чата или глобальным админом."""
    if user_id in settings.ADMIN_IDS:
        return True
    
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
