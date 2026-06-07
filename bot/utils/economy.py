"""
Economy utils: register users, award wins, convert diamonds, transfer.
"""
from __future__ import annotations

from bot.config import settings
from bot.database.crud import (
    get_or_create_user, log_transaction, update_balance
)
from bot.database.engine import AsyncSessionLocal


async def register_user(
    user_id: int,
    username: str | None,
    full_name: str | None,
    ref_id: int | None = None,
) -> bool:
    """Регистрирует нового пользователя. Возвращает True если создан."""
    async with AsyncSessionLocal() as session:
        user, created = await get_or_create_user(session, user_id, username, full_name, ref_id)
        if created:
            await log_transaction(
                session, user_id, settings.STARTING_COINS, "coins",
                "registration", "Стартовые монеты"
            )
        await session.commit()
    return created


async def award_win(user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        await update_balance(session, user_id, delta_coins=settings.WIN_REWARD_COINS)
        await log_transaction(session, user_id, settings.WIN_REWARD_COINS, "coins", "win")
        await session.commit()


async def convert_diamonds(user_id: int, amount: int) -> tuple[bool, str]:
    """Конвертация алмазов в монеты. Возвращает (success, message)."""
    async with AsyncSessionLocal() as session:
        user, _ = await get_or_create_user(session, user_id)
        if user.diamonds < amount:
            return False, f"Недостаточно алмазов. У вас: {user.diamonds} 💎"
        coins_gained = amount * settings.DIAMOND_TO_COINS_RATE
        await update_balance(session, user_id, delta_coins=coins_gained, delta_diamonds=-amount)
        await log_transaction(session, user_id, -amount, "diamonds", "convert")
        await log_transaction(session, user_id, coins_gained, "coins", "convert",
                              f"Конвертация {amount} алм. → {coins_gained} монет")
        await session.commit()
    return True, f"✅ Обменяно {amount} 💎 → {coins_gained} 🪙"


async def transfer_diamonds(
    from_id: int, to_id: int, amount: int
) -> tuple[bool, str]:
    """Передача алмазов между игроками."""
    if from_id == to_id:
        return False, "Нельзя переводить себе."
    if amount <= 0:
        return False, "Сумма должна быть > 0."
    async with AsyncSessionLocal() as session:
        sender, _ = await get_or_create_user(session, from_id)
        receiver, _ = await get_or_create_user(session, to_id)
        if sender.diamonds < amount:
            return False, f"Недостаточно алмазов. У вас: {sender.diamonds} 💎"
        await update_balance(session, from_id, delta_diamonds=-amount)
        await update_balance(session, to_id, delta_diamonds=amount)
        await log_transaction(session, from_id, -amount, "diamonds", "transfer",
                              f"Перевод → {to_id}")
        await log_transaction(session, to_id, amount, "diamonds", "transfer",
                              f"Получено от {from_id}")
        await session.commit()
    return True, f"✅ Переведено {amount} 💎 → {receiver.username or to_id}"
