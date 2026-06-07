"""
Admin Bot commands with user_id middleware auth.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Router
from aiogram.filters import Command
from aiogram.types import Message, TelegramObject

from bot.config import settings
from bot.database.crud import (
    add_chat, get_all_active_chats, get_all_user_ids, get_inventory,
    get_or_create_user, get_user, log_transaction, remove_chat,
    set_ban, update_balance,
)
from bot.database.engine import AsyncSessionLocal

router = Router()

# ─────────────────── Admin Middleware ────────────────────────────

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            if event.from_user and event.from_user.id not in settings.ADMIN_IDS:
                await event.answer("🚫 Нет доступа.")
                return
        return await handler(event, data)


# ─────────────────── Chat Whitelist ──────────────────────────────

@router.message(Command("addchat"))
async def cmd_addchat(message: Message, bot: Bot):
    """
    /addchat <chat_id> [title]
    Добавить чат в белый список. Если вызвано в нужном чате без аргументов — добавит текущий.
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Использование: /addchat <chat_id> [title]")
        return
    try:
        chat_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный chat_id.")
        return
    title = args[2] if len(args) > 2 else None

    try:
        chat_info = await bot.get_chat(chat_id)
        title = title or chat_info.title or str(chat_id)
    except Exception:
        title = title or str(chat_id)

    async with AsyncSessionLocal() as session:
        await add_chat(session, chat_id, title, message.from_user.id)
        await session.commit()
    await message.answer(f"✅ Чат <b>{title}</b> (<code>{chat_id}</code>) добавлен в белый список.", parse_mode="HTML")


@router.message(Command("delchat"))
async def cmd_delchat(message: Message):
    """/delchat <chat_id>"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /delchat <chat_id>")
        return
    try:
        chat_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный chat_id.")
        return

    async with AsyncSessionLocal() as session:
        ok = await remove_chat(session, chat_id)
        await session.commit()

    if ok:
        await message.answer(f"✅ Чат <code>{chat_id}</code> удалён из белого списка.", parse_mode="HTML")
    else:
        await message.answer("⚠️ Чат не найден в белом списке.")


@router.message(Command("listchats"))
async def cmd_listchats(message: Message):
    async with AsyncSessionLocal() as session:
        chats = await get_all_active_chats(session)
    if not chats:
        await message.answer("Список чатов пуст.")
        return
    lines = [f"• <code>{c.id}</code> {c.title or '—'}" for c in chats]
    await message.answer("📋 <b>Белый список чатов:</b>\n" + "\n".join(lines), parse_mode="HTML")


# ─────────────────── Currency ─────────────────────────────────────

@router.message(Command("give_diamonds"))
async def cmd_give_diamonds(message: Message):
    """/give_diamonds <user_id> <amount>"""
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /give_diamonds <user_id> <amount>")
        return
    try:
        uid, amount = int(args[1]), int(args[2])
    except ValueError:
        await message.answer("❌ Неверный формат.")
        return

    if amount < 0:
        await message.answer("❌ Количество должно быть >= 0.")
        return

    async with AsyncSessionLocal() as session:
        user, _ = await get_or_create_user(session, uid)
        await update_balance(session, uid, delta_diamonds=amount)
        await log_transaction(session, uid, amount, "diamonds", "admin_give",
                              f"Выдано админом {message.from_user.id}")
        await session.commit()

    await message.answer(f"✅ Выдано {amount} 💎 пользователю <code>{uid}</code>.", parse_mode="HTML")


@router.message(Command("take_diamonds"))
async def cmd_take_diamonds(message: Message):
    """/take_diamonds <user_id> <amount>"""
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /take_diamonds <user_id> <amount>")
        return
    try:
        uid, amount = int(args[1]), int(args[2])
    except ValueError:
        await message.answer("❌ Неверный формат.")
        return

    async with AsyncSessionLocal() as session:
        await update_balance(session, uid, delta_diamonds=-amount)
        await log_transaction(session, uid, -amount, "diamonds", "admin_take",
                              f"Изъято админом {message.from_user.id}")
        await session.commit()

    await message.answer(f"✅ Изъято {amount} 💎 у пользователя <code>{uid}</code>.", parse_mode="HTML")


@router.message(Command("give_coins"))
async def cmd_give_coins(message: Message):
    """/give_coins <user_id> <amount>"""
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /give_coins <user_id> <amount>")
        return
    try:
        uid, amount = int(args[1]), int(args[2])
    except ValueError:
        await message.answer("❌ Неверный формат.")
        return

    async with AsyncSessionLocal() as session:
        await update_balance(session, uid, delta_coins=amount)
        await log_transaction(session, uid, amount, "coins", "admin_give")
        await session.commit()

    await message.answer(f"✅ Выдано {amount} 🪙 пользователю <code>{uid}</code>.", parse_mode="HTML")


@router.message(Command("take_coins"))
async def cmd_take_coins(message: Message):
    """/take_coins <user_id> <amount>"""
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /take_coins <user_id> <amount>")
        return
    try:
        uid, amount = int(args[1]), int(args[2])
    except ValueError:
        await message.answer("❌ Неверный формат.")
        return

    async with AsyncSessionLocal() as session:
        await update_balance(session, uid, delta_coins=-amount)
        await log_transaction(session, uid, -amount, "coins", "admin_take")
        await session.commit()

    await message.answer(f"✅ Изъято {amount} 🪙 у пользователя <code>{uid}</code>.", parse_mode="HTML")


# ─────────────────── Moderation ──────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot):
    """/ban <user_id> [reason]"""
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Использование: /ban <user_id> [reason]")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный user_id.")
        return
    reason = args[2] if len(args) > 2 else "Нарушение правил"

    async with AsyncSessionLocal() as session:
        await set_ban(session, uid, True)
        await session.commit()

    await message.answer(f"🔨 Пользователь <code>{uid}</code> заблокирован.\nПричина: {reason}", parse_mode="HTML")
    try:
        await bot.send_message(uid, f"🚫 Вы заблокированы.\nПричина: {reason}")
    except Exception:
        pass


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot):
    """/unban <user_id>"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /unban <user_id>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный user_id.")
        return

    async with AsyncSessionLocal() as session:
        await set_ban(session, uid, False)
        await session.commit()

    await message.answer(f"✅ Пользователь <code>{uid}</code> разблокирован.", parse_mode="HTML")
    try:
        await bot.send_message(uid, "✅ Вы разблокированы. Добро пожаловать обратно!")
    except Exception:
        pass


@router.message(Command("info"))
async def cmd_info(message: Message):
    """/info <user_id> — полный профиль пользователя"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /info <user_id>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный user_id.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user(session, uid)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return
        inv = await get_inventory(session, uid)

    wr = 0
    if user.games_played > 0:
        wr = round(user.games_won / user.games_played * 100)

    inv_str = ", ".join(f"{i.item_type}×{i.quantity}" for i in inv) or "пусто"
    banned_str = "🔴 Заблокирован" if user.is_banned else "🟢 Активен"

    text = (
        f"👤 <b>Профиль #{uid}</b>\n"
        f"Ник: @{user.username or '—'}\n"
        f"Имя: {user.full_name or '—'}\n"
        f"Статус: {banned_str}\n\n"
        f"💰 Монеты: {user.coins}\n"
        f"💎 Алмазы: {user.diamonds}\n\n"
        f"🎮 Игр: {user.games_played} | Побед: {user.games_won} ({wr}%)\n"
        f"🎒 Инвентарь: {inv_str}\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y') if user.created_at else '—'}"
    )
    await message.answer(text, parse_mode="HTML")


# ─────────────────── Broadcast ───────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    """/broadcast <текст> — рассылка всем пользователям"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /broadcast <текст>")
        return
    text = args[1]

    async with AsyncSessionLocal() as session:
        user_ids = await get_all_user_ids(session)

    await message.answer(f"📢 Начинаю рассылку для {len(user_ids)} пользователей...")

    ok, fail = 0, 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 <b>Объявление:</b>\n{text}", parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)  # Anti-flood

    await message.answer(f"✅ Рассылка завершена.\nДоставлено: {ok} | Ошибок: {fail}")


# ─────────────────── Settings & Prices ────────────────────────────

@router.message(Command("set_price"))
async def cmd_set_price(message: Message):
    """/set_price <role_name> <price_diamonds>"""
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /set_price <role_name> <price_diamonds>")
        return
    
    from bot.game.roles import RoleName
    role_input = args[1].lower()
    try:
        # Валидация роли
        role_name = RoleName(role_input)
    except ValueError:
        await message.answer(f"❌ Некорректная роль: {role_input}")
        return
    
    try:
        price = int(args[2])
        if price < 0: raise ValueError
    except ValueError:
        await message.answer("❌ Цена должна быть числом >= 0.")
        return

    from bot.database.crud import set_setting
    async with AsyncSessionLocal() as session:
        await set_setting(session, f"role_price_{role_input}", str(price))
        await session.commit()
    
    status = f"установлена: {price}💎" if price > 0 else "удалена из магазина (0💎)"
    await message.answer(f"✅ Цена для роли <b>{role_name.value}</b> {status}.", parse_mode="HTML")


@router.message(Command("prices"))
async def cmd_prices(message: Message):
    """Показать текущие цены на роли."""
    from bot.database.crud import get_all_role_prices
    async with AsyncSessionLocal() as session:
        prices = await get_all_role_prices(session)
    
    lines = ["🎭 <b>Текущие цены на роли:</b>"]
    for role_name, price in sorted(prices.items(), key=lambda x: (-x[1], x[0])):
        if price == 0: continue
        lines.append(f"• <code>{role_name}</code>: {price} 💎")
    
    if len(lines) == 1:
        await message.answer("Магазин ролей пуст.")
    else:
        await message.answer("\n".join(lines), parse_mode="HTML")


# ─────────────────── Help ────────────────────────────────────────

@router.message(Command("start", "help"))
async def cmd_admin_help(message: Message):
    text = (
        "🛠 <b>Admin Bot — команды:</b>\n\n"
        "<b>Белый список:</b>\n"
        "/addchat &lt;chat_id&gt; [title]\n"
        "/delchat &lt;chat_id&gt;\n"
        "/listchats\n\n"
        "<b>Валюта:</b>\n"
        "/give_diamonds &lt;uid&gt; &lt;n&gt;\n"
        "/take_diamonds &lt;uid&gt; &lt;n&gt;\n"
        "/give_coins &lt;uid&gt; &lt;n&gt;\n"
        "/take_coins &lt;uid&gt; &lt;n&gt;\n\n"
        "<b>Настройки:</b>\n"
        "/set_price &lt;role&gt; &lt;diamonds&gt; — изменить цену роли\n"
        "/prices — список цен\n\n"
        "<b>Модерация:</b>\n"
        "/ban &lt;uid&gt; [reason]\n"
        "/unban &lt;uid&gt;\n"
        "/info &lt;uid&gt;\n\n"
        "<b>Рассылка:</b>\n"
        "/broadcast &lt;текст&gt;"
    )
    await message.answer(text, parse_mode="HTML")

