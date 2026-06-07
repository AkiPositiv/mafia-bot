"""add lang column to chats

Revision ID: d001
Revises: c18b758a84f4
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd001'
down_revision: Union[str, None] = 'c18b758a84f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chats', sa.Column('lang', sa.String(5), nullable=False, server_default='ru'))


def downgrade() -> None:
    op.drop_column('chats', 'lang')
