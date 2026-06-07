"""
Main entry point: Game Bot.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats

from bot.config import settings
from bot.database.engine import engine
from bot.database.models import Base
from bot.middleware import BanCheckMiddleware, WhitelistMiddleware, GameChatGuardMiddleware

from bot.handlers.game.moderation import router as moderation_router
from bot.handlers.game.lobby import router as lobby_router
from bot.handlers.game.night import router as night_router
from bot.handlers.game.vote import router as vote_router
from bot.handlers.game.shop import router as shop_router
from bot.handlers.common.profile import router as profile_router
from bot.handlers.common.member import router as member_router
from bot.handlers.game.leaderboard import router as leaderboard_router
from bot.handlers.game.last_word import router as last_word_router
from bot.handlers.admin.commands import AdminMiddleware, manage_router as admin_manage_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Создать таблицы (для разработки). В prod используй Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def main() -> None:
    await create_tables()

    bot = Bot(
        token=settings.GAME_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Commands scoping
    await bot.set_my_commands(
        [
            BotCommand(command="profile", description="👤 Мой профиль"),
            BotCommand(command="shop",    description="🛒 Магазин"),
            BotCommand(command="ref",     description="🔗 Реферальная ссылка"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        [
            BotCommand(command="newgame",  description="🎮 Создать игру"),
            BotCommand(command="start",    description="🚀 Запустить (Админ)"),
            BotCommand(command="extend",   description="⏳ Продлить (Админ)"),
            BotCommand(command="stopgame", description="🛑 Остановить (Админ)"),
            BotCommand(command="stop",     description="🛑 Остановить (Админ)"),
            BotCommand(command="mute",     description="🔇 Мут (Админ)"),
            BotCommand(command="unmute",   description="🔊 Размут (Админ)"),
            BotCommand(command="warn",     description="⚠️ Варн (Админ)"),
            BotCommand(command="unwarn",   description="✅ Снять варны (Админ)"),
            BotCommand(command="unban",    description="✅ Разбан (Админ)"),
            BotCommand(command="call",     description="🔔 Позвать всех (Админ)"),
            BotCommand(command="leave",    description="🚪 Покинуть лобби"),
            BotCommand(command="top",      description="🏆 Топ игроков"),
        ],
        scope=BotCommandScopeAllGroupChats()
    )

    # Middlewares
    dp.message.middleware(BanCheckMiddleware())
    dp.message.middleware(WhitelistMiddleware())
    dp.message.middleware(GameChatGuardMiddleware())

    # Routers - profile_router MUST come before lobby_router for /start deep links
    dp.include_router(moderation_router)
    dp.include_router(member_router)        # join/leave events — must be early
    dp.include_router(profile_router)
    dp.include_router(lobby_router)
    dp.include_router(night_router)
    dp.include_router(vote_router)
    dp.include_router(shop_router)
    dp.include_router(leaderboard_router)
    dp.include_router(last_word_router)

    # Admin commands available in private chat (/adminhelp to see the list)
    _admin_gate = Router()
    _admin_gate.message.filter(F.chat.type == "private")
    _admin_gate.message.middleware(AdminMiddleware())
    _admin_gate.include_router(admin_manage_router)
    dp.include_router(_admin_gate)

    logger.info("Game Bot starting...")
    try:
        allowed = list(dp.resolve_used_update_types()) + ["chat_member"]
        await dp.start_polling(bot, allowed_updates=list(set(allowed)))
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
