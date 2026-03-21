"""repair_missing_turn_audio_expiration

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
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
    conn = op.get_bind()
    inspector = inspect(conn)
    turns_columns = [col["name"] for col in inspector.get_columns("turns", schema="core")]

    if "audio_expires_at" in turns_columns:
        op.drop_column("turns", "audio_expires_at", schema="core")
