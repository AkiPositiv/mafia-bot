"""
Leaderboard handler: /top command
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.crud import get_top_winrate
from bot.database.engine import AsyncSessionLocal

router = Router()

@router.message(Command("top"))
async def cmd_top(message: Message):
    """Отображает топ игроков по проценту побед."""
    async with AsyncSessionLocal() as session:
        top_users = await get_top_winrate(session, limit=10)
    
    if not top_users:
        await message.answer("📊 Рейтинг пока пуст. Нужно сыграть минимум 5 игр.")
        return

    text = "🏆 <b>Топ игроков (по % побед):</b>\n\n"
    for i, user in enumerate(top_users, 1):
        wr = (user.games_won * 100 / user.games_played) if user.games_played > 0 else 0
        name = user.full_name or user.username or f"ID:{user.id}"
        text += f"{i}. 👤 <b>{name}</b> — {wr:.1f}% ({user.games_won}/{user.games_played})\n"
    
    await message.answer(text, parse_mode="HTML")
