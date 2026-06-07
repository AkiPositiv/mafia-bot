"""
GameRegistry — глобальный реестр активных GameEngine по chat_id.
Используется хендлерами для доступа к текущей игре.
"""
from __future__ import annotations

from bot.game.engine import GameEngine

_registry: dict[int, GameEngine] = {}  # chat_id → GameEngine


def register(chat_id: int, engine: GameEngine) -> None:
    _registry[chat_id] = engine


def get(chat_id: int) -> GameEngine | None:
    return _registry.get(chat_id)


def remove(chat_id: int) -> None:
    _registry.pop(chat_id, None)


def get_by_game_id(game_id: int) -> GameEngine | None:
    """Найти игру по её ID (из базы)."""
    for engine in _registry.values():
        if engine.game_id == game_id:
            return engine
    return None


def get_by_user_id(user_id: int) -> GameEngine | None:
    """Найти игру, в которой участвует игрок."""
    for engine in _registry.values():
        if user_id in engine.players:
            return engine
    return None


async def restore_game(game_id: int, bot) -> GameEngine | None:
    """Восстанавливает GameEngine из БД после рестарта."""
    from bot.database.engine import AsyncSessionLocal
    from bot.database.crud import get_game_with_players
    from bot.game.engine import GameEngine, PlayerState
    from bot.game.notify import make_notify
    from bot.game.roles import RoleName
    import asyncio
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as session:
        game = await get_game_with_players(session, game_id)
        if not game or game.status == "finished":
            return None
        
        notify_cb = await make_notify(bot, game.chat_id, None)
        engine = GameEngine(game.id, game.chat_id, notify_cb)
        notify_cb_real = await make_notify(bot, game.chat_id, engine)
        engine._notify = notify_cb_real
        
        # Восстанавливаем игроков
        for p in game.players:
            ps = PlayerState(
                user_id=p.user_id,
                username=p.user.username or p.user.full_name,
                role=RoleName(p.role) if p.role else RoleName.CIVILIAN,
                is_alive=p.is_alive,
                has_vest=p.has_vest,
                has_docs=p.has_docs,
            )
            if p.poison_day is not None:
                ps.poison_day = p.poison_day
            engine.players[p.user_id] = ps
        
        # Восстанавливаем параметры лобби
        engine.lobby_message_id = game.lobby_message_id
        if game.lobby_end_time:
            now = datetime.now(timezone.utc)
            rem_seconds = (game.lobby_end_time - now).total_seconds()
            if rem_seconds > 0:
                engine.lobby_end_time = asyncio.get_event_loop().time() + rem_seconds
                # Перезапускаем таймер
                await engine.start_lobby(rem_seconds)
            else:
                # Время вышло, пока бот лежал?
                # Можно либо сразу завершить, либо дать еще 10 секунд
                engine.lobby_end_time = asyncio.get_event_loop().time() + 10
                await engine.start_lobby(10)

        register(game.chat_id, engine)
        return engine
