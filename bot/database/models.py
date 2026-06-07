from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)          # Telegram user_id
    username = Column(String(64), nullable=True)
    full_name = Column(String(128), nullable=True)
    coins = Column(Integer, default=50, nullable=False)
    diamonds = Column(Integer, default=0, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    warn_count = Column(Integer, default=0, nullable=False)
    games_played = Column(Integer, default=0, nullable=False)
    games_won = Column(Integer, default=0, nullable=False)
    referred_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Loadout (Active items for the next game)
    active_shield = Column(Boolean, default=False, nullable=False)
    active_docs = Column(Boolean, default=False, nullable=False)
    active_bullet = Column(Boolean, default=False, nullable=False)
    active_role = Column(String(32), nullable=True)  # RoleName value if set

    inventory = relationship("Inventory", back_populates="user", cascade="all, delete-orphan")
    referrals_sent = relationship(
        "Referral", foreign_keys="Referral.referrer_id", back_populates="referrer"
    )
    referral_received = relationship(
        "Referral", foreign_keys="Referral.referee_id", back_populates="referee", uselist=False
    )
    game_players = relationship("GamePlayer", back_populates="user")
    transactions = relationship("TransactionLog", back_populates="user")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(32), nullable=False)   # shield, docs, silver_bullet, role_<name>
    quantity = Column(Integer, default=1, nullable=False)

    user = relationship("User", back_populates="inventory")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True)          # Telegram chat_id
    title = Column(String(256), nullable=True)
    added_by = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    lang = Column(String(5), default="ru", nullable=False)  # ru | uz
    added_at = Column(DateTime(timezone=True), server_default=func.now())


class TransactionLog(Base):
    __tablename__ = "transactions_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)           # positive = credit, negative = debit
    currency = Column(String(16), nullable=False)       # coins | diamonds
    tx_type = Column(String(32), nullable=False)        # win, buy_item, admin_give, referral, etc.
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")


class GameHistory(Base):
    __tablename__ = "game_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    winner_team = Column(String(32), nullable=True)     # town | mafia | neutral | nobody
    players_json = Column(Text, nullable=True)          # JSON snapshot
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referee_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rewarded_days_mask = Column(Integer, default=0, nullable=False)   # bitmask days 1-7
    games_today = Column(Integer, default=0, nullable=False)
    last_game_date = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("referee_id"),)

    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_sent")
    referee = relationship("User", foreign_keys=[referee_id], back_populates="referral_received")


class Game(Base):
    """Active / finished game session."""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    creator_id = Column(BigInteger, nullable=False)
    status = Column(String(16), default="lobby")       # lobby | night | day | vote | finished
    phase_number = Column(Integer, default=0)           # 0 = not started, 1..N round counter
    winner_team = Column(String(32), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Persistence for lobby state
    lobby_message_id = Column(BigInteger, nullable=True)
    lobby_end_time = Column(DateTime(timezone=True), nullable=True)

    players = relationship("GamePlayer", back_populates="game", cascade="all, delete-orphan")


class BotSetting(Base):
    """
    Ключ-значение настройки бота, изменяемые через Admin Bot.
    Пример: key='role_price_don', value='3'
    """
    __tablename__ = "bot_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(256), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GamePlayer(Base):
    """Участник конкретной игры."""
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=True)
    is_alive = Column(Boolean, default=True, nullable=False)
    has_vest = Column(Boolean, default=False, nullable=False)      # бронежилет
    has_docs = Column(Boolean, default=False, nullable=False)      # документы
    is_blocked = Column(Boolean, default=False, nullable=False)    # заблокирован путаной/барменом
    is_immune_vote = Column(Boolean, default=False, nullable=False)  # иммунитет от голосования (адвокат)
    poison_day = Column(Integer, nullable=True)                    # номер дня, когда умрёт от яда

    __table_args__ = (UniqueConstraint("game_id", "user_id"),)

    game = relationship("Game", back_populates="players")
    user = relationship("User", back_populates="game_players")
