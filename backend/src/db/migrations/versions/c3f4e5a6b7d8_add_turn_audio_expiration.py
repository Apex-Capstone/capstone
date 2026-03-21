"""add_turn_audio_expiration

Revision ID: c3f4e5a6b7d8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c3f4e5a6b7d8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    turns_columns = [col["name"] for col in inspector.get_columns("turns", schema="core")]

    if "audio_expires_at" not in turns_columns:
        op.add_column(
            "turns",
            sa.Column("audio_expires_at", sa.DateTime(), nullable=True),
            schema="core",
        )


def downgrade() -> None:
    op.drop_column("turns", "audio_expires_at", schema="core")
