"""Keyboards for the game bot."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.game.engine import PlayerState
from bot.game.roles import RoleName


def join_keyboard(game_id: int, bot_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    url = f"https://t.me/{bot_username}?start=join_{game_id}"
    builder.button(text="➕ Присоединиться", url=url)
    return builder.as_markup()


def players_target_keyboard(players: list[PlayerState], action: str, game_id: int,
                             exclude_ids: list[int] | None = None) -> InlineKeyboardMarkup:
    """Inline-клавиатура выбора цели из живых игроков."""
    exclude = set(exclude_ids or [])
    builder = InlineKeyboardBuilder()
    for p in players:
        if p.is_alive and p.user_id not in exclude:
            builder.button(
                text=f"👤 {p.username}",
                callback_data=f"{action}:{game_id}:{p.user_id}",
            )
    builder.button(text="⏭ Пропустить", callback_data=f"{action}:{game_id}:skip")
    builder.adjust(2)
    return builder.as_markup()


def mafia_vote_keyboard(players: list[PlayerState], game_id: int) -> InlineKeyboardMarkup:
    """Мафия выбирает жертву совместно."""
    builder = InlineKeyboardBuilder()
    for p in players:
        if p.is_alive and p.role not in (RoleName.MAFIA, RoleName.DON, RoleName.NINJA, RoleName.LAWYER, RoleName.WEREWOLF):
            builder.button(
                text=f"🎯 {p.username}",
                callback_data=f"mafia_kill:{game_id}:{p.user_id}",
            )
    builder.button(text="⏭ Не убивать", callback_data=f"mafia_kill:{game_id}:skip")
    builder.adjust(2)
    return builder.as_markup()


def day_vote_keyboard(players: list[PlayerState], voter_id: int, game_id: int) -> InlineKeyboardMarkup:
    """Дневное голосование."""
    builder = InlineKeyboardBuilder()
    for p in players:
        if p.is_alive and p.user_id != voter_id:
            builder.button(
                text=f"☠️ {p.username}",
                callback_data=f"vote:{game_id}:{p.user_id}",
            )
    builder.button(text="🚫 Воздержаться", callback_data=f"vote:{game_id}:skip")
    builder.adjust(2)
    return builder.as_markup()


def commissioner_action_keyboard(game_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Проверить", callback_data=f"com_choose:{game_id}:check")
    builder.button(text="🔫 Выстрелить", callback_data=f"com_choose:{game_id}:shoot")
    builder.adjust(2)
    return builder.as_markup()


def shop_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡 Щит — 150 монет", callback_data="shop:shield")
    builder.button(text="📄 Документы — 200 монет", callback_data="shop:docs")
    builder.button(text="🥈 Сер. пуля — 1 💎", callback_data="shop:silver_bullet")
    builder.button(text="🎭 Купить роль — 1-3 💎", callback_data="shop:role_menu")
    builder.button(text="📖 Роли и описания", callback_data="roles:menu")
    builder.button(text="◀ В профиль", callback_data="profile:main")
    builder.adjust(1)
    return builder.as_markup()


def shop_roles_keyboard(roles_data: list[tuple[str, str, int]]) -> InlineKeyboardMarkup:
    """roles_data = [(label, role_name, price_diamonds)]"""
    builder = InlineKeyboardBuilder()
    for label, role_name, price in roles_data:
        builder.button(
            text=f"{label} — {price}💎",
            callback_data=f"shop:buy_role:{role_name}",
        )
    builder.button(text="◀ Назад", callback_data="shop:back")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm:{action}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def exchange_keyboard(rates: dict[int, int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for diamonds, coins in rates.items():
        builder.button(
            text=f"💎 {diamonds} → {coins} 🪙",
            callback_data=f"shop:ex:{diamonds}:{coins}"
        )
    builder.button(text="◀ Назад", callback_data="shop:exchange")
    builder.adjust(1)
    return builder.as_markup()


def purchase_keyboard(prices: dict[int, dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for qty, p in prices.items():
        builder.button(
            text=f"💎 {qty} за {p['stars']} ⭐ (≈{p['usd']}$)",
            callback_data=f"shop:buy_stars:{qty}"
        )
    builder.button(text="◀ Назад", callback_data="shop:exchange")
    builder.adjust(1)
    return builder.as_markup()


def bank_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔃 Обмен 💎 → 🪙", callback_data="shop:ex_menu")
    builder.button(text="💎 Купить Алмазы", callback_data="shop:buy_menu")
    builder.button(text="◀ Назад", callback_data="profile:main")
    builder.adjust(1)
    return builder.as_markup()

def trial_keyboard(game_id: int, likes: int = 0, dislikes: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"👍 Повесить ({likes})", callback_data=f"trial_vote:{game_id}:like")
    kb.button(text=f"👎 Помиловать ({dislikes})", callback_data=f"trial_vote:{game_id}:dislike")
    return kb.as_markup()


def back_to_chat_button(chat_id: int, game_id: int) -> InlineKeyboardMarkup:
    """Кнопка 'Перейти в чат' для DM-сообщений."""
    from bot.game import registry as _reg
    engine = _reg.get(chat_id)
    msg_id = (engine.lobby_message_id or 1) if engine else 1
    inner = str(chat_id).replace('-100', '')
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Перейти в чат", url=f"https://t.me/c/{inner}/{msg_id}")
    return kb.as_markup()

