"""
Referral system: 7-day progression tracking, daily rewards.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from aiogram import Bot

from bot.config import settings
from bot.database.crud import (
    get_referral, create_referral, log_transaction, update_balance
)
from bot.database.engine import AsyncSessionLocal

# Награды по дням: день→монеты (день 7 → 1 алмаз)
DAY_REWARDS: dict[int, tuple[int, str]] = {
    1: (30, "coins"),
    2: (40, "coins"),
    3: (50, "coins"),
    4: (60, "coins"),
    5: (70, "coins"),
    6: (80, "coins"),
    7: (1, "diamonds"),
}


async def setup_referral(referee_id: int, referrer_id: int) -> None:
    """Создать реферальную связь при регистрации."""
    async with AsyncSessionLocal() as session:
        await create_referral(session, referrer_id, referee_id)
        await session.commit()


async def process_game_for_referrals(bot: Bot, player_ids: list[int]) -> None:
    """
    Вызывается после каждой игры. Для каждого игрока, кто является рефералом,
    засчитываем игровой день и при необходимости выдаём награду пригласившему.
    """
    today = date.today()
    async with AsyncSessionLocal() as session:
        for uid in player_ids:
            ref = await get_referral(session, uid)
            if not ref:
                continue

            # Проверяем: уже играл сегодня?
            last_game = ref.last_game_date
            if last_game and last_game.date() == today:
                continue  # уже засчитан сегодня

            ref.last_game_date = datetime.now(timezone.utc)
            ref.games_today += 1

            # Определяем текущий "день прогрессии"
            current_day = bin(ref.rewarded_days_mask).count("1") + 1
            if current_day > 7:
                continue  # прогрессия завершена

            # Засчитываем день (bitmask)
            ref.rewarded_days_mask |= (1 << (current_day - 1))

            # Выдаём награду
            amount, currency = DAY_REWARDS[current_day]
            if currency == "coins":
                await update_balance(session, ref.referrer_id, delta_coins=amount)
            else:
                await update_balance(session, ref.referrer_id, delta_diamonds=amount)

            await log_transaction(
                session, ref.referrer_id, amount, currency,
                "referral", f"Реферал день {current_day}"
            )

            # Уведомляем реферрера
            try:
                label = f"{amount} {'монет' if currency == 'coins' else '💎'}"
                await bot.send_message(
                    ref.referrer_id,
                    f"🎁 <b>Реферальная награда!</b>\n"
                    f"Ваш реферал сыграл день {current_day}.\n"
                    f"Вы получили: +{label}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await session.commit()
