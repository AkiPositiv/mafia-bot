"""
Lobby handlers: /newgame, /join, /start, /extend, /endgame
"""
from __future__ import annotations

import asyncio
from typing import Optional
from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.crud import (
    add_player_to_game, create_game, get_active_game, get_or_create_user,
    remove_player_from_game
)
from bot.database.engine import AsyncSessionLocal
from bot.game.engine import GameEngine
from bot.game.notify import make_notify
from bot.game import registry
from bot.keyboards.game_kb import join_keyboard
from bot.utils.permissions import is_admin
import logging
logger = logging.getLogger(__name__)

router = Router()


def _format_lobby_text(engine: GameEngine) -> str:
    """Форматирует сообщение лобби на русском."""
    players = list(engine.players.values())
    count = len(players)
    
    text = "🎮 <b>Набор игроков в новую игру!</b>\n\n"
    text += f"👥 <b>Игроки ({count}):</b>\n"
    for i, p in enumerate(players, 1):
        text += f"{i}. 👤 {p.username}\n"
    
    # Расчет времени
    rem = int(max(0, engine.lobby_end_time - asyncio.get_event_loop().time()))
    mins = rem // 60
    secs = rem % 60
    
    text += f"\n⏳ <b>До конца набора:</b> {mins:02d}:{secs:02d}\n"
    if count < settings.MIN_PLAYERS:
        text += f"⚠️ Нужно еще минимум {settings.MIN_PLAYERS - count} чел."
    else:
        text += "✅ Можно начинать (/start)"
    
    return text


@router.message(Command("newgame"))
async def cmd_newgame(message: Message, bot: Bot):
    if message.chat.type == "private":
        await message.answer("❌ Игру можно создать только в группе.")
        return

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("❌ Только администраторы чата могут создавать игры.")
        return

    async with AsyncSessionLocal() as session:
        existing = await get_active_game(session, message.chat.id)
        if existing:
            # Кросс-проверка: если игры нет в реестре — БД устарела, закрываем её
            from bot.game import registry as game_registry
            if game_registry.get(message.chat.id) is None:
                logger.warning(
                    f"Stale active game {existing.id} in DB for chat {message.chat.id} — force-closing."
                )
                existing.status = "finished"
                await session.commit()
                # existing теперь закрыта, продолжаем создавать новую
            else:
                await message.answer("⚠️ В этом чате уже есть активная игра!")
                return

        user = message.from_user
        await get_or_create_user(session, user.id, user.username, user.full_name)
        game = await create_game(session, message.chat.id, user.id)
        await session.commit()
        game_id = game.id

    notify_cb = await make_notify(bot, message.chat.id, None)
    engine = GameEngine(game_id, message.chat.id, notify_cb)
    notify_cb_real = await make_notify(bot, message.chat.id, engine)
    engine._notify = notify_cb_real

    engine.add_player(user.id, user.full_name or user.username)
    registry.register(message.chat.id, engine)

    # Запуск таймера в движке
    await engine.start_lobby()

    bot_info = await bot.get_me()
    msg = await message.answer(
        _format_lobby_text(engine),
        reply_markup=join_keyboard(game_id, bot_info.username),
        parse_mode="HTML",
    )
    engine.lobby_message_id = msg.message_id
    
    # Сохраняем ID сообщения и время окончания в БД для восстановления после рестарта
    async with AsyncSessionLocal() as session:
        game = await get_active_game(session, message.chat.id)
        if game:
            game.lobby_message_id = msg.message_id
            from datetime import datetime, timezone, timedelta
            # asyncio.get_event_loop().time() это монотонное время, но нам нужно настенное
            engine.lobby_end_time = asyncio.get_event_loop().time() + settings.LOBBY_DURATION
            game.lobby_end_time = datetime.now(timezone.utc) + timedelta(seconds=settings.LOBBY_DURATION)
            await session.commit()

    try:
        await bot.pin_chat_message(message.chat.id, msg.message_id)
    except Exception:
        pass


@router.message(Command("join"))
async def cmd_join(message: Message, bot: Bot):
    engine = registry.get(message.chat.id)
    if not engine:
        # Попробуем восстановить из БД
        async with AsyncSessionLocal() as session:
            game = await get_active_game(session, message.chat.id)
            if game and game.status == "lobby":
                engine = await registry.restore_game(game.id, bot)

    if not engine or engine.phase != "lobby":
        return

    bot_info = await bot.get_me()
    res = await process_player_join(engine, message.from_user, bot, bot_info.username)
    await message.answer(res)

async def process_player_join(engine: GameEngine, user: types.User, bot: Bot, bot_username: str) -> str:
    """Общая логика входа игрока в лобби."""
    logger.info(f"Processing join: user={user.id} ({user.username}) game={engine.game_id} in {engine.chat_id}")
    if len(engine.players) >= settings.MAX_PLAYERS:
        return "❌ Достигнут лимит игроков."

    async with AsyncSessionLocal() as session:
        await get_or_create_user(session, user.id, user.username, user.full_name)
        await add_player_to_game(session, engine.game_id, user.id)
        await session.commit()

    if engine.add_player(user.id, user.full_name or user.username):
        # Оповещение в группу
        try:
            await bot.send_message(
                engine.chat_id, 
                f"✅ <b>{user.username or user.full_name}</b> вошёл в игру!",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send join notification to group {engine.chat_id}: {e}")

        # Обновляем главное сообщение лобби
        if engine.lobby_message_id:
            try:
                text = _format_lobby_text(engine)
                kb = join_keyboard(engine.game_id, bot_username)
                await bot.edit_message_text(
                    chat_id=engine.chat_id,
                    message_id=engine.lobby_message_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
                logger.info(f"Updated lobby UI for game {engine.game_id} (msg: {engine.lobby_message_id})")
            except Exception as e:
                logger.error(f"Failed to edit lobby UI {engine.lobby_message_id}: {e}")
        
        # Получаем название чата для красивого ответа
        chat_title = "игру"
        try:
            chat = await bot.get_chat(engine.chat_id)
            chat_title = f"игру в чате «{chat.title}»"
        except Exception:
            pass

        return f"✅ Вы успешно присоединились к {chat_title}! Ждите начала."
    else:
        return "⚠️ Вы уже в игре!"


@router.message(Command("leave"))
async def cmd_leave(message: Message):
    engine = registry.get(message.chat.id)
    if not engine or engine.phase != "lobby":
        return

    user = message.from_user
    async with AsyncSessionLocal() as session:
        ok = await remove_player_from_game(session, engine.game_id, user.id)
        await session.commit()

    if engine.remove_player(user.id):
        await message.answer(f"🚪 <b>{user.username or user.full_name}</b> покинул лобби.", parse_mode="HTML")
    else:
        await message.answer("❌ Вас нет в списке участников.")





@router.message(Command("extend"))
async def cmd_extend(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    
    engine = registry.get(message.chat.id)
    if not engine or engine.phase != "lobby":
        return
    
    new_dur = await engine.extend_lobby()
    if new_dur:
        await message.answer(f"➕ Регистрация продлена на 30 сек! (Всего: {new_dur // 60}:{new_dur % 60:02d})")
        # Обновить лобби-сообщение если возможно? (Сложно отследить конкретное сообщение, но можно отправить новое)




@router.message(Command("start"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_startgame_admin(message: Message, bot: Bot):
    """Досрочный старт игры (только админ)."""
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    # Пробуем найти или восстановить игру
    engine = registry.get(message.chat.id)
    if not engine:
        async with AsyncSessionLocal() as session:
            game = await get_active_game(session, message.chat.id)
            if game:
                engine = await registry.restore_game(game.id, bot)
    
    if not engine:
        return

    if engine.phase != "lobby":
        return

    n = engine.get_player_count()
    if n < settings.MIN_PLAYERS:
        await message.answer(f"❌ Нужно минимум {settings.MIN_PLAYERS} игрока. Сейчас: {n}.")
        return

    # Начинаем игру
    await message.answer("🚀 Игра запускается досрочно!")
    await engine.start_game()


@router.message(Command("endgame", "stopgame", "stop"))
async def cmd_endgame(message: Message, bot: Bot):
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return

    # Пробуем найти или восстановить (даже если игра не в лобби, cmd_endgame обработает)
    engine = registry.get(message.chat.id)
    game_id = None

    if engine:
        if engine._phase_task:
            engine._phase_task.cancel()
        game_id = engine.game_id
        registry.remove(message.chat.id)
    else:
        # Пытаемся найти игру в БД, если в памяти её нет (после рестарта)
        async with AsyncSessionLocal() as session:
            existing = await get_active_game(session, message.chat.id)
            if existing:
                game_id = existing.id
    
    if not game_id:
        await message.answer("❌ Нет активной игры для завершения.")
        return

    async with AsyncSessionLocal() as session:
        from bot.database.crud import finish_game
        await finish_game(session, game_id, "cancelled", [])
        await session.commit()

    await message.answer("🛑 Игра принудительно завершена (без статистики).")
