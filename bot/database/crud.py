"""
CRUD — все операции с базой данных.
Каждая функция принимает AsyncSession и возвращает ORM-объект или None.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Union

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    BotSetting, Chat, Game, GamePlayer, GameHistory,
    Inventory, Referral, TransactionLog, User
)
from bot.config import settings


# ─────────────────────────── USERS ────────────────────────────

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    referred_by: Optional[int] = None,
) -> tuple[User, bool]:
    """Возвращает (user, created)."""
    user = await get_user(session, user_id)
    if user:
        # Обновляем имя при каждом обращении
        if username and user.username != username:
            user.username = username
        if full_name and user.full_name != full_name:
            user.full_name = full_name
        return user, False

    user = User(
        id=user_id,
        username=username,
        full_name=full_name,
        coins=settings.STARTING_COINS,
        diamonds=0,
        referred_by=referred_by,
    )
    session.add(user)
    await session.flush()
    return user, True


async def update_balance(
    session: AsyncSession,
    user_id: int,
    delta_coins: int = 0,
    delta_diamonds: int = 0,
) -> User:
    user = await get_user(session, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    user.coins = max(0, user.coins + delta_coins)
    user.diamonds = max(0, user.diamonds + delta_diamonds)
    return user


async def set_ban(session: AsyncSession, user_id: int, banned: bool) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(is_banned=banned)
    )


async def toggle_loadout(
    session: AsyncSession,
    user_id: int,
    item_key: str,
    value: Union[bool, str, None],
) -> User:
    user = await get_user(session, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    if item_key == "shield": user.active_shield = bool(value)
    elif item_key == "docs": user.active_docs = bool(value)
    elif item_key == "bullet": user.active_bullet = bool(value)
    elif item_key == "role": user.active_role = value if value else None
    
    return user


async def get_top_winrate(session: AsyncSession, limit: int = 10) -> list[User]:
    """Топ по проценту побед (мин. 5 сыгранных игр)."""
    result = await session.execute(
        select(User)
        .where(User.games_played >= 5)
        .order_by((User.games_won * 100 / User.games_played).desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ─────────────────────────── INVENTORY ────────────────────────

async def get_inventory(session: AsyncSession, user_id: int) -> list[Inventory]:
    result = await session.execute(
        select(Inventory).where(Inventory.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_item(
    session: AsyncSession, user_id: int, item_type: str
) -> Optional[Inventory]:
    result = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_type == item_type,
        )
    )
    return result.scalar_one_or_none()


async def add_item(session: AsyncSession, user_id: int, item_type: str, qty: int = 1) -> Inventory:
    row = await get_item(session, user_id, item_type)
    if row:
        row.quantity += qty
    else:
        row = Inventory(user_id=user_id, item_type=item_type, quantity=qty)
        session.add(row)
    await session.flush()
    return row


async def remove_item(
    session: AsyncSession, user_id: int, item_type: str, qty: int = 1
) -> bool:
    """Returns True if removed successfully."""
    row = await get_item(session, user_id, item_type)
    if not row or row.quantity < qty:
        return False
    row.quantity -= qty
    if row.quantity == 0:
        await session.delete(row)
    await session.flush()
    return True


# ─────────────────────────── CHATS ────────────────────────────

async def get_chat(session: AsyncSession, chat_id: int) -> Optional[Chat]:
    result = await session.execute(select(Chat).where(Chat.id == chat_id))
    return result.scalar_one_or_none()


async def add_chat(
    session: AsyncSession,
    chat_id: int,
    title: Optional[str],
    added_by: int,
) -> Chat:
    chat = await get_chat(session, chat_id)
    if chat:
        chat.is_active = True
        chat.title = title or chat.title
    else:
        chat = Chat(id=chat_id, title=title, added_by=added_by, is_active=True)
        session.add(chat)
    await session.flush()
    return chat


async def remove_chat(session: AsyncSession, chat_id: int) -> bool:
    chat = await get_chat(session, chat_id)
    if not chat:
        return False
    chat.is_active = False
    return True


async def get_all_active_chats(session: AsyncSession) -> list[Chat]:
    result = await session.execute(select(Chat).where(Chat.is_active == True))
    return list(result.scalars().all())


# ─────────────────────────── TRANSACTIONS ─────────────────────

async def log_transaction(
    session: AsyncSession,
    user_id: int,
    amount: int,
    currency: str,
    tx_type: str,
    note: Optional[str] = None,
) -> TransactionLog:
    tx = TransactionLog(
        user_id=user_id,
        amount=amount,
        currency=currency,
        tx_type=tx_type,
        note=note,
    )
    session.add(tx)
    await session.flush()
    return tx


# ─────────────────────────── GAMES ────────────────────────────

async def get_active_game(session: AsyncSession, chat_id: int) -> Optional[Game]:
    """Возвращает незавершённую игру в чате."""
    result = await session.execute(
        select(Game)
        .where(Game.chat_id == chat_id, Game.status != "finished")
        .options(selectinload(Game.players).selectinload(GamePlayer.user))
    )
    return result.scalar_one_or_none()


async def create_game(
    session: AsyncSession, 
    chat_id: int, 
    creator_id: int, 
    lobby_message_id: Optional[int] = None,
    lobby_end_time: Optional[datetime] = None
) -> Game:
    game = Game(
        chat_id=chat_id, 
        creator_id=creator_id, 
        status="lobby", 
        lobby_message_id=lobby_message_id,
        lobby_end_time=lobby_end_time
    )
    session.add(game)
    await session.flush()
    return game


async def get_game_simple(session: AsyncSession, game_id: int) -> Optional[Game]:
    """Быстрый запрос игры по ID без подгрузки игроков."""
    result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    return result.scalar_one_or_none()


async def get_game_with_players(session: AsyncSession, game_id: int) -> Optional[Game]:
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.players).selectinload(GamePlayer.user))
    )
    return result.scalar_one_or_none()


async def add_player_to_game(
    session: AsyncSession, game_id: int, user_id: int
) -> Optional[GamePlayer]:
    # Проверяем дубли
    result = await session.execute(
        select(GamePlayer).where(
            GamePlayer.game_id == game_id, GamePlayer.user_id == user_id
        )
    )
    if result.scalar_one_or_none():
        return None
    gp = GamePlayer(game_id=game_id, user_id=user_id)
    session.add(gp)
    await session.flush()
    return gp


async def remove_player_from_game(session: AsyncSession, game_id: int, user_id: int) -> bool:
    result = await session.execute(
        delete(GamePlayer).where(
            GamePlayer.game_id == game_id, GamePlayer.user_id == user_id
        )
    )
    await session.flush()
    return result.rowcount > 0


async def finish_game(
    session: AsyncSession,
    game_id: int,
    winner_team: str,
    players_snapshot: list[dict],
) -> None:
    game = await session.get(Game, game_id)
    if not game:
        return
    game.status = "finished"
    game.winner_team = winner_team
    game.finished_at = datetime.now(timezone.utc)

    history = GameHistory(
        chat_id=game.chat_id,
        winner_team=winner_team,
        players_json=json.dumps(players_snapshot, ensure_ascii=False),
    )
    session.add(history)
    await session.flush()


# ─────────────────────────── REFERRALS ────────────────────────

async def get_referral(session: AsyncSession, referee_id: int) -> Optional[Referral]:
    result = await session.execute(
        select(Referral).where(Referral.referee_id == referee_id)
    )
    return result.scalar_one_or_none()


async def create_referral(
    session: AsyncSession, referrer_id: int, referee_id: int
) -> Optional[Referral]:
    existing = await get_referral(session, referee_id)
    if existing:
        return None
    ref = Referral(referrer_id=referrer_id, referee_id=referee_id)
    session.add(ref)
    await session.flush()
    return ref


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    """Для broadcast."""
    result = await session.execute(select(User.id).where(User.is_banned == False))
    return list(result.scalars().all())


# ─────────────────────────── BOT SETTINGS ─────────────────────

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    result = await session.execute(
        select(BotSetting).where(BotSetting.key == key)
    )
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_setting(session: AsyncSession, key: str, value: str) -> BotSetting:
    row = await session.get(BotSetting, key)
    if row:
        row.value = value
    else:
        row = BotSetting(key=key, value=value)
        session.add(row)
    await session.flush()
    return row


async def get_all_role_prices(session: AsyncSession) -> dict[str, int]:
    """
    Возвращает итоговые цены ролей: default + DB-оверрайды.
    Ключ = role_name (str), значение = цена в алмазах.
    """
    from bot.config import DEFAULT_ROLE_PRICES
    prices = dict(DEFAULT_ROLE_PRICES)
    result = await session.execute(
        select(BotSetting).where(BotSetting.key.startswith("role_price_"))
    )
    for row in result.scalars().all():
        role_name = row.key[len("role_price_"):]
        try:
            prices[role_name] = int(row.value)
        except ValueError:
            pass
    return prices

