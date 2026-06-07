from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bots
    GAME_BOT_TOKEN: str = ""
    ADMIN_BOT_TOKEN: str = ""

    # Database
    # Railway предоставляет postgresql://, конвертируем в postgresql+asyncpg://
    DATABASE_URL: str = "postgresql+asyncpg://mafia:mafia_secret@localhost:5432/mafia_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_async_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Admins (comma-separated or single ID in .env)
    ADMIN_IDS: List[int] = []

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, int, List[int]]) -> List[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    # Economy defaults
    STARTING_COINS: int = 50
    WIN_REWARD_COINS: int = 30
    DIAMOND_TO_COINS_RATE: int = 100

    # Shop prices (overridable via .env)
    PRICE_SHIELD_COINS: int = 150
    PRICE_DOCS_COINS: int = 200
    PRICE_SILVER_BULLET_DIAMONDS: int = 1

    # Game phase timings (seconds)
    LOBBY_DURATION: int = 180      # 3 minutes
    EXTEND_DURATION: int = 30
    NIGHT_DURATION: int = 30
    DAY_DURATION: int = 25
    VOTE_DURATION: int = 35

    # Currency Exchange (Diamonds -> Coins)
    # 1:200, 2:500, 3:800, 4:1200
    EXCHANGE_RATES: dict[int, int] = {
        1: 200,
        2: 500,
        3: 800,
        4: 1200
    }

    # Diamond Prices (Stars / USD)
    # 1:10/0.16, 5:50/0.75, 10:100/1.1, 20:200/2.1
    DIAMOND_PRICES: dict[int, dict] = {
        1:  {"stars": 10,  "usd": 0.16},
        5:  {"stars": 50,  "usd": 0.75},
        10: {"stars": 100, "usd": 1.1},
        20: {"stars": 200, "usd": 2.1},
    }

    # Game limits
    MIN_PLAYERS: int = 4
    MAX_PLAYERS: int = 30


settings = Settings()

# ── Цены ролей по умолчанию (переопределяются через Admin Bot → DB) ──
# Ключ: RoleName.value (строка), значение: цена в алмазах
# 0 = роль не продаётся
DEFAULT_ROLE_PRICES: dict[str, int] = {
    # 3 💎 — топовые роли
    "don":          3,
    "commissioner": 3,
    "ninja":        3,
    "maniac":       3,
    # 2 💎 — сильные роли
    "armorer":      2,
    "terrorist":    2,
    "werewolf":     2,
    "necromancer":  2,
    "poisoner":     2,
    "bartender":    2,
    # 1 💎 — обычные роли
    "doctor":       1,
    "prostitute":   1,
    "journalist":   1,
    "witness":      1,
    "sergeant":     1,
    "jester":       1,
    "mayor":        1,
    "lawyer":       1,
    "mafia":        1,
    # 0 = не продаётся
    "civilian":     0,
}
