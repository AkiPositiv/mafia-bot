"""
Profile, /start (with referral), /ref, /convert, /transfer handlers.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.database.crud import get_inventory, get_or_create_user, get_user, toggle_loadout
from bot.database.engine import AsyncSessionLocal
from bot.game.roles import ALL_ROLES
from bot.utils.economy import convert_diamonds, register_user, transfer_diamonds
from bot.utils.referral import setup_referral
from bot.game import registry
import logging
logger = logging.getLogger(__name__)

router = Router()

def _get_profile_text(user) -> str:
    wr = (user.games_won * 100 / user.games_played) if user.games_played > 0 else 0
    text = f"👤 <b>Профиль: {user.full_name}</b>\n\n"
    text += f"💰 Монеты: <code>{user.coins}</code> 🪙\n"
    text += f"💎 Алмазы: <code>{user.diamonds}</code> 💎\n\n"
    text += f"📊 <b>Статистика:</b>\n"
    text += f"🎮 Игр сыграно: {user.games_played}\n"
    text += f"🏆 Побед: {user.games_won}\n"
    text += f"📈 Процент побед: {wr:.1f}%\n"
    return text

def _get_menu_kb(user, inventory) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    # Считаем количество предметов
    items = {item.item_type: item.quantity for item in inventory}
    
    # Щит
    shield_qty = items.get("shield", 0)
    shield_btn = f"🛡 Щит: {'✅' if user.active_shield else '❌'} (x{shield_qty})" if shield_qty > 0 else "🛡 Щит: (нет)"
    builder.button(text=shield_btn, callback_data="loadout:shield")
    
    # Документы
    docs_qty = items.get("docs", 0)
    docs_btn = f"📄 Документы: {'✅' if user.active_docs else '❌'} (x{docs_qty})" if docs_qty > 0 else "📄 Документы: (нет)"
    builder.button(text=docs_btn, callback_data="loadout:docs")
    
    # Серебряная пуля
    bullet_qty = items.get("silver_bullet", 0)
    bullet_btn = f"🥈 Сер. пуля: {'✅' if user.active_bullet else '❌'} (x{bullet_qty})" if bullet_qty > 0 else "🥈 Сер. пуля: (нет)"
    builder.button(text=bullet_btn, callback_data="loadout:bullet")
    
    # Активная роль
    role_items = {k[5:]: v for k, v in items.items() if k.startswith("role_")}
    if role_items:
        role_btn = "🎭 Выбрать роль"
        if user.active_role:
            _role_obj = ALL_ROLES.get(user.active_role)
            role_label = _role_obj.label if _role_obj else user.active_role
            qty = role_items.get(user.active_role, 0)
            role_btn = f"🎭 {role_label} ✅ (x{qty})"
        builder.button(text=role_btn, callback_data="profile:role_select")
    else:
        builder.button(text="🎭 Роль: (нет)", callback_data="none")

    builder.button(text="🛒 Магазин", callback_data="shop:main")
    builder.button(text="🏦 Обмен / Покупка 💎", callback_data="shop:exchange")
    
    builder.adjust(1)
    return builder.as_markup()


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message):
    """Регистрация + обработка реферальной ссылки."""
    user = message.from_user
    ref_id: int | None = None

    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        param = args[1]
        # Обработка реферала
        if param.startswith("ref_"):
            try:
                ref_id = int(param[4:])
                if ref_id == user.id:
                    ref_id = None  # Нельзя пригласить себя
            except ValueError:
                ref_id = None
        
        # Обработка входа в игру
        elif param.startswith("join_"):
            try:
                game_id = int(param[5:])
                logger.info(f"User {user.id} attempting to join game {game_id} via deep link")
                
                from bot.handlers.game.lobby import process_player_join
                engine = registry.get_by_game_id(game_id)
                if not engine:
                    logger.info(f"Game {game_id} not in registry, attempting restoration...")
                    engine = await registry.restore_game(game_id, message.bot)

                if engine and engine.phase == "lobby":
                    bot_info = await message.bot.get_me()
                    logger.info(f"Triggering process_player_join for game {game_id}")
                    res = await process_player_join(engine, user, message.bot, bot_info.username)
                    await message.answer(res)
                    logger.info(f"Join successful for user {user.id}")
                    return
                else:
                    logger.warning(f"Join failed: engine is {type(engine)} phase is {engine.phase if engine else 'N/A'}")
                    await message.answer("❌ Игра не найдена или уже началась.")
                    return
            except Exception as e:
                logger.exception(f"CRITICAL ERROR in join flow for user {user.id}: {e}")
                await message.answer("❌ Произошла ошибка при входе в игру. Попробуйте еще раз.")
                return

    created = await register_user(user.id, user.username, user.full_name, ref_id)

    if created and ref_id:
        await setup_referral(user.id, ref_id)
        await message.answer(
            f"🎉 <b>Добро пожаловать!</b>\n"
            f"Вы зарегистрированы по реферальной ссылке.\n"
            f"Стартовый баланс: <b>{settings.STARTING_COINS} монет</b> 🪙",
            parse_mode="HTML",
        )
    elif created:
        await message.answer(
            f"🎉 <b>Добро пожаловать в Мафию!</b>\n"
            f"Стартовый баланс: <b>{settings.STARTING_COINS} монет</b> 🪙\n\n"
            f"📋 /profile — ваш профиль\n"
            f"🏪 /shop — магазин\n"
            f"🔗 /ref — реферальная ссылка",
            parse_mode="HTML",
        )
    else:
        await message.answer("👋 С возвращением! Напишите /profile.")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Карточка игрока с меню снаряжения."""
    if message.chat.type != "private":
        await message.answer("❌ Профиль доступен только в ЛС.")
        return

    async with AsyncSessionLocal() as session:
        user, _ = await get_or_create_user(
            session, message.from_user.id,
            message.from_user.username, message.from_user.full_name
        )
        inventory = await get_inventory(session, user.id)
        await session.commit()
    
    await message.answer(
        _get_profile_text(user),
        reply_markup=_get_menu_kb(user, inventory),
        parse_mode="HTML"
    )

@router.callback_query(F.data.in_({"profile:refresh", "profile:main"}))
async def cb_profile_refresh(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        user = await get_user(session, callback.from_user.id)
        if not user: return
        inventory = await get_inventory(session, user.id)
        await session.commit()
    
    await callback.message.edit_text(
        _get_profile_text(user),
        reply_markup=_get_menu_kb(user, inventory),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "profile:role_select")
async def cb_profile_role_select(callback: CallbackQuery):
    """Показать меню выбора роли из инвентаря."""
    async with AsyncSessionLocal() as session:
        user = await get_user(session, callback.from_user.id)
        if not user: return
        inventory = await get_inventory(session, user.id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    role_items = {it.item_type[5:]: it.quantity for it in inventory if it.item_type.startswith("role_")}
    
    for role_name, qty in role_items.items():
        role_info = ALL_ROLES.get(role_name)
        if not role_info: continue
        
        status = "✅" if user.active_role == role_name else ""
        builder.button(
            text=f"{role_info.emoji} {role_info.label} x{qty} {status}",
            callback_data=f"role_select:{role_name}"
        )
    
    builder.button(text="❌ Сбросить выбор", callback_data="role_select:none")
    builder.button(text="🔙 Назад", callback_data="profile:main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🎭 <b>Выбор роли для следующего матча:</b>\n"
        "Выберите роль, которую хотите получить в следующей игре:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("role_select:"))
async def cb_role_select_apply(callback: CallbackQuery):
    role_name = callback.data.split(":")[1]
    if role_name == "none": role_name = None
    
    async with AsyncSessionLocal() as session:
        await toggle_loadout(session, callback.from_user.id, "role", role_name)
        await session.commit()
    
    await callback.answer(f"✅ Роль {'выбрана' if role_name else 'сброшена'}")
    await cb_profile_role_select(callback)

@router.callback_query(F.data.startswith("loadout:"))
async def cb_loadout_toggle(callback: CallbackQuery):
    item = callback.data.split(":")[1]
    async with AsyncSessionLocal() as session:
        user = await get_user(session, callback.from_user.id)
        if not user: return
        inventory = await get_inventory(session, user.id)
        items = {it.item_type: it.quantity for it in inventory}
        
        if item == "shield":
            if items.get("shield", 0) > 0:
                await toggle_loadout(session, user.id, "shield", not user.active_shield)
            else:
                await callback.answer("❌ У вас нет щита!", show_alert=True)
                return
        elif item == "docs":
            if items.get("docs", 0) > 0:
                await toggle_loadout(session, user.id, "docs", not user.active_docs)
            else:
                await callback.answer("❌ У вас нет документов!", show_alert=True)
                return
        elif item == "bullet":
            if items.get("silver_bullet", 0) > 0:
                await toggle_loadout(session, user.id, "bullet", not user.active_bullet)
            else:
                await callback.answer("❌ У вас нет серебряной пули!", show_alert=True)
                return
        await session.commit()
    
    await cb_profile_refresh(callback)


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    """Реферальная ссылка."""
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    text = (
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{link}</code>\n\n"
        f"📈 <b>Прогрессия наград:</b>\n"
        f"День 1: 30🪙 | День 2: 40🪙 | День 3: 50🪙\n"
        f"День 4: 60🪙 | День 5: 70🪙 | День 6: 80🪙\n"
        f"День 7: 1💎\n\n"
        f"Реферал должен сыграть хотя бы 1 игру в день."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("convert"))
async def cmd_convert(message: Message):
    """Конвертация алмазов: /convert <количество>"""
    args = message.text.split()
    if len(args) < 2:
        rate = settings.DIAMOND_TO_COINS_RATE
        await message.answer(f"Использование: /convert [количество]\nКурс: 1💎 = {rate}🪙")
        return
    try:
        amount = int(args[1])
    except ValueError:
        await message.answer("❌ Укажите число.")
        return
    ok, msg = await convert_diamonds(message.from_user.id, amount)
    await message.answer(msg)


@router.message(Command("transfer"))
async def cmd_transfer(message: Message):
    """
    Передача алмазов.
    1. /transfer (в ответ на сообщение) -> 1 алмаз
    2. /transfer <количество> (в ответ на сообщение) -> N алмазов
    3. /transfer <user_id> <количество> -> N алмазов через ID
    """
    target_id: int | None = None
    target_name: str | None = None
    amount: int = 1

    args = message.text.split()
    
    # Сценарий с реплеем
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if target_user.is_bot:
            await message.answer("❌ Нельзя переводить алмазы ботам.")
            return
        target_id = target_user.id
        target_name = target_user.full_name
        
        if len(args) > 1:
            try:
                amount = int(args[1])
            except ValueError:
                await message.answer("❌ Укажите количество числом: /transfer [количество]")
                return
    
    # Сценарий через ID
    elif len(args) >= 3:
        try:
            target_id = int(args[1])
            amount = int(args[2])
        except ValueError:
            await message.answer("❌ Неверный формат. Используйте: /transfer [ID] [количество]")
            return
    else:
        await message.answer(
            "📚 <b>Использование:</b>\n"
            "• Ответьте на сообщение: <code>/transfer [количество]</code>\n"
            "• Через ID: <code>/transfer [ID] [количество]</code>",
            parse_mode="HTML"
        )
        return

    if target_id == message.from_user.id:
        await message.answer("❌ Нельзя переводить алмазы самому себе.")
        return

    if amount <= 0:
        await message.answer("❌ Количество должно быть больше 0.")
        return

    ok, msg = await transfer_diamonds(message.from_user.id, target_id, amount)

    # Удаляем сообщение-команду
    try:
        await message.delete()
    except Exception:
        pass

    if ok:
        sender_tag = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>"
        recv_name = target_name or str(target_id)
        recv_tag = f"<a href='tg://user?id={target_id}'>{recv_name}</a>"
        await message.answer(
            f"💎 {sender_tag} передал {amount} 💎 → {recv_tag}",
            parse_mode="HTML"
        )
    else:
        await message.answer(msg)

