"""Alembic generic single-database configuration."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(64), nullable=True),
        sa.Column('full_name', sa.String(128), nullable=True),
        sa.Column('coins', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('diamonds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('games_played', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('games_won', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('referred_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['referred_by'], ['users.id']),
    )

    # Bot Settings
    op.create_table(
        'bot_settings',
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('value', sa.String(256), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key'),
    )

    # Inventory
    op.create_table(
        'inventory',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('item_type', sa.String(32), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Chats
    op.create_table(
        'chats',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(256), nullable=True),
        sa.Column('added_by', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Transactions log
    op.create_table(
        'transactions_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(16), nullable=False),
        sa.Column('tx_type', sa.String(32), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Game history
    op.create_table(
        'game_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('winner_team', sa.String(32), nullable=True),
        sa.Column('players_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
    )

    # Referrals
    op.create_table(
        'referrals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('referrer_id', sa.BigInteger(), nullable=False),
        sa.Column('referee_id', sa.BigInteger(), nullable=False),
        sa.Column('rewarded_days_mask', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('games_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_game_date', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referee_id'),
        sa.ForeignKeyConstraint(['referrer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['referee_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Games
    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('creator_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='lobby'),
        sa.Column('phase_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winner_team', sa.String(32), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id']),
    )

    # Game players
    op.create_table(
        'game_players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(32), nullable=True),
        sa.Column('is_alive', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('has_vest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_docs', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_immune_vote', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('poison_day', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'user_id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    op.drop_table('game_players')
    op.drop_table('games')
    op.drop_table('referrals')
    op.drop_table('game_history')
    op.drop_table('transactions_log')
    op.drop_table('chats')
    op.drop_table('inventory')
    op.drop_table('users')
