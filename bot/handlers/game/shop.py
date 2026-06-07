"""
Shop handler: /shop command, item purchases, role purchases with dynamic DB pricing.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import settings
from bot.database.crud import (
    add_item, get_all_role_prices, get_inventory, get_or_create_user,
    get_user, log_transaction, remove_item, update_balance,
)
from bot.database.engine import AsyncSessionLocal
from bot.game.roles import ALL_ROLES, RoleName
from bot.keyboards.game_kb import shop_main_keyboard, shop_roles_keyboard

def _back_to_shop_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀ В магазин", callback_data="shop:main")
    return builder.as_markup()

router = Router()


async def _role_shop_items(session) -> list[tuple[str, str, int]]:
    """Возвращает список (label, role_value, price) для ролей с ценой > 0."""
    prices = await get_all_role_prices(session)
    items = []
    for role_value, price in sorted(prices.items(), key=lambda x: (-x[1], x[0])):
        if price == 0:
            continue
        try:
            role = ALL_ROLES[RoleName(role_value)]
        except (ValueError, KeyError):
            continue
        label = f"{role.emoji} {role.label} — {price}💎"
        items.append((label, role_value, price))
    return items


async def _send_main_shop_menu(event: Message | CallbackQuery, user_id: int):
    """Общий хелпер для показа меню магазина."""
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
        coins = user.coins if user else 0
        diamonds = user.diamonds if user else 0

    text = (
        f"🏪 <b>Магазин</b>\n\n"
        f"💰 Монеты: <b>{coins}</b>\n"
        f"💎 Алмазы: <b>{diamonds}</b>\n\n"
        f"🛡 Щит — {settings.PRICE_SHIELD_COINS}🪙 (1 ночь защиты)\n"
        f"📄 Документы — {settings.PRICE_DOCS_COINS}🪙 (маскировка при проверке)\n"
        f"🥈 Серебряная пуля — {settings.PRICE_SILVER_BULLET_DIAMONDS}💎 (игнорирует щит)\n"
        f"🎭 Роли — от 1💎\n\n"
        f"Выберите товар:"
    )
    kb = shop_main_keyboard()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("shop"))
async def cmd_shop(message: Message):
    """Открыть магазин (только в ЛС)."""
    if message.chat.type != "private":
        await message.answer("🏪 Магазин доступен в личных сообщениях с ботом.")
        return
    await _send_main_shop_menu(message, message.from_user.id)


@router.callback_query(F.data.in_({"shop:main", "shop:back"}))
async def cb_shop_main(callback: CallbackQuery):
    await callback.answer()
    await _send_main_shop_menu(callback, callback.from_user.id)


@router.callback_query(F.data == "shop:shield")
async def cb_buy_shield(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_user(session, uid)
        if not user or user.coins < settings.PRICE_SHIELD_COINS:
            await callback.message.answer(
                f"❌ Недостаточно монет. Нужно: {settings.PRICE_SHIELD_COINS} 🪙"
            )
            return
        await update_balance(session, uid, delta_coins=-settings.PRICE_SHIELD_COINS)
        await add_item(session, uid, "shield")
        await log_transaction(session, uid, -settings.PRICE_SHIELD_COINS, "coins", "buy_shield")
        await session.commit()
    await callback.message.edit_text(
        f"✅ Куплен <b>Щит</b> (-{settings.PRICE_SHIELD_COINS} 🪙)\n"
        "Защищает от одного ночного выстрела (кроме Ниндзи).",
        reply_markup=_back_to_shop_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "shop:docs")
async def cb_buy_docs(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_user(session, uid)
        if not user or user.coins < settings.PRICE_DOCS_COINS:
            await callback.message.answer(
                f"❌ Недостаточно монет. Нужно: {settings.PRICE_DOCS_COINS} 🪙"
            )
            return
        await update_balance(session, uid, delta_coins=-settings.PRICE_DOCS_COINS)
        await add_item(session, uid, "docs")
        await log_transaction(session, uid, -settings.PRICE_DOCS_COINS, "coins", "buy_docs")
        await session.commit()
    await callback.message.edit_text(
        f"✅ Куплены <b>Документы</b> (-{settings.PRICE_DOCS_COINS} 🪙)\n"
        "При проверке Комиссара вы будете выглядеть как Мирный житель.",
        reply_markup=_back_to_shop_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "shop:silver_bullet")
async def cb_buy_silver_bullet(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_user(session, uid)
        if not user or user.diamonds < settings.PRICE_SILVER_BULLET_DIAMONDS:
            await callback.message.answer(
                f"❌ Недостаточно алмазов. Нужно: {settings.PRICE_SILVER_BULLET_DIAMONDS} 💎"
            )
            return
        await update_balance(session, uid, delta_diamonds=-settings.PRICE_SILVER_BULLET_DIAMONDS)
        await add_item(session, uid, "silver_bullet")
        await log_transaction(
            session, uid, -settings.PRICE_SILVER_BULLET_DIAMONDS, "diamonds", "buy_silver_bullet"
        )
        await session.commit()
    await callback.message.edit_text(
        f"✅ Куплена <b>Серебряная пуля</b> (-{settings.PRICE_SILVER_BULLET_DIAMONDS} 💎)\n"
        "Игнорирует щиты. Доступна только ролям-убийцам.",
        reply_markup=_back_to_shop_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "shop:role_menu")
async def cb_role_menu(callback: CallbackQuery):
    await callback.answer()
    async with AsyncSessionLocal() as session:
        items = await _role_shop_items(session)

    if not items:
        await callback.message.answer("🎭 Нет доступных ролей для покупки.")
        return

    await callback.message.edit_text(
        "🎭 <b>Купить роль на следующий матч:</b>\n"
        "⚠️ При коллизии роль назначается случайному покупателю.",
        reply_markup=shop_roles_keyboard(items),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("shop:buy_role:"))
async def cb_buy_role(callback: CallbackQuery):
    await callback.answer()
    _, _, role_value = callback.data.split(":", 2)

    try:
        role_name = RoleName(role_value)
    except ValueError:
        await callback.message.answer("❌ Неизвестная роль.")
        return

    uid = callback.from_user.id
    async with AsyncSessionLocal() as session:
        prices = await get_all_role_prices(session)
        price = prices.get(role_value, 0)
        if price == 0:
            await callback.message.answer("❌ Эта роль не продаётся.")
            return

        user = await get_user(session, uid)
        if not user or user.diamonds < price:
            await callback.message.answer(f"❌ Недостаточно алмазов. Нужно: {price} 💎")
            return

        await update_balance(session, uid, delta_diamonds=-price)
        await add_item(session, uid, f"role_{role_value}")
        
        # Автоматически ставим новую роль активной
        user.active_role = role_value
        
        role = ALL_ROLES[role_name]
        await log_transaction(session, uid, -price, "diamonds", "buy_role", f"Роль: {role.label}")
        await session.commit()

    await callback.message.edit_text(
        f"✅ Роль <b>{role.emoji} {role.label}</b> куплена (-{price} 💎)\n"
        "Будет выдана в следующем матче (если нет коллизии).",
        reply_markup=_back_to_shop_kb(),
        parse_mode="HTML",
    )



@router.callback_query(F.data == "shop:exchange")
async def cb_shop_exchange_menu(callback: CallbackQuery):
    await callback.answer()
    from bot.keyboards.game_kb import bank_keyboard
    
    await callback.message.edit_text(
        "🏦 <b>Банк Мафии</b>\n\n"
        "Выберите желаемое действие:\n"
        "• <b>Обменять</b> Алмазы на Монеты\n"
        "• <b>Приобрести</b> Алмазы (Telegram Stars)",
        reply_markup=bank_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "shop:ex_menu")
async def cb_ex_menu(callback: CallbackQuery):
    await callback.answer()
    from bot.keyboards.game_kb import exchange_keyboard
    await callback.message.edit_text(
        "🔃 <b>Обмен Алмазов на Монеты</b>\n"
        "Выберите выгодный курс:",
        reply_markup=exchange_keyboard(settings.EXCHANGE_RATES),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("shop:ex:"))
async def cb_execute_exchange(callback: CallbackQuery):
    _, _, d_str, c_str = callback.data.split(":")
    diamonds_req = int(d_str)
    coins_gain = int(c_str)
    
    uid = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await get_user(session, uid)
        if not user or user.diamonds < diamonds_req:
            await callback.answer(f"❌ Недостаточно алмазов ({diamonds_req} 💎)", show_alert=True)
            return
        
        await update_balance(session, uid, delta_diamonds=-diamonds_req, delta_coins=coins_gain)
        await log_transaction(session, uid, -diamonds_req, "diamonds", "exchange")
        await log_transaction(session, uid, coins_gain, "coins", "exchange")
        await session.commit()
    
    await callback.answer(f"✅ Обмен совершен! +{coins_gain} 🪙", show_alert=True)
    await cb_ex_menu(callback)


@router.callback_query(F.data == "shop:buy_menu")
async def cb_buy_menu(callback: CallbackQuery):
    await callback.answer()
    from bot.keyboards.game_kb import purchase_keyboard
    await callback.message.edit_text(
        "💎 <b>Покупка Алмазов</b>\n"
        "Выберите пакет (через Telegram Stars):",
        reply_markup=purchase_keyboard(settings.DIAMOND_PRICES),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("shop:buy_stars:"))
async def cb_buy_stars_stub(callback: CallbackQuery):
    # Заглушка для платежей. В реальном боте здесь выставляется инвойс.
    qty = callback.data.split(":")[2]
    await callback.answer("⏳ Функция оплаты через Telegram Stars будет доступна в ближайшем обновлении!", show_alert=True)
