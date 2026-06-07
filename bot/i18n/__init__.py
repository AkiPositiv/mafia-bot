"""
i18n — система локализации бота.

Использование:
    from bot.i18n import t, get_lang, set_lang

    lang = await get_lang(chat_id)    # "ru" | "uz"
    text = t("game_started", lang, count=10)
"""
from __future__ import annotations

import logging
from typing import Optional

from bot.i18n.strings_ru import STRINGS as STRINGS_RU
from bot.i18n.strings_uz import STRINGS as STRINGS_UZ

logger = logging.getLogger(__name__)

_ALL_STRINGS: dict[str, dict[str, str]] = {
    "ru": STRINGS_RU,
    "uz": STRINGS_UZ,
}

# In-memory cache: chat_id → lang code
_lang_cache: dict[int, str] = {}

DEFAULT_LANG = "ru"


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Получить локализованную строку по ключу."""
    strings = _ALL_STRINGS.get(lang, STRINGS_RU)
    template = strings.get(key)
    if template is None:
        # fallback to Russian
        template = STRINGS_RU.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


async def get_lang(chat_id: int) -> str:
    """Получить язык чата (из кэша или БД)."""
    if chat_id in _lang_cache:
        return _lang_cache[chat_id]

    # Fetch from DB
    try:
        from bot.database.engine import AsyncSessionLocal
        from bot.database.models import Chat
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = select(Chat.lang).where(Chat.id == chat_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            lang = row if row else DEFAULT_LANG
    except Exception:
        lang = DEFAULT_LANG

    _lang_cache[chat_id] = lang
    return lang


async def set_lang(chat_id: int, lang: str) -> None:
    """Установить язык чата (обновляет БД и кэш)."""
    from bot.database.engine import AsyncSessionLocal
    from bot.database.models import Chat
    from sqlalchemy import update

    async with AsyncSessionLocal() as session:
        stmt = update(Chat).where(Chat.id == chat_id).values(lang=lang)
        await session.execute(stmt)
        await session.commit()

    _lang_cache[chat_id] = lang


def get_role_label(role_name: str, lang: str = DEFAULT_LANG) -> str:
    """Получить локализованное название роли."""
    return t(f"role_{role_name}_label", lang)


def get_role_desc(role_name: str, lang: str = DEFAULT_LANG) -> str:
    """Получить локализованное описание роли."""
    return t(f"role_{role_name}_desc", lang)


def get_role_goal(role_name: str, lang: str = DEFAULT_LANG) -> str:
    """Получить локализованную цель роли."""
    return t(f"role_{role_name}_goal", lang)


def get_team_name(team: str, lang: str = DEFAULT_LANG) -> str:
    """Получить название команды."""
    return t(f"team_{team}", lang)
