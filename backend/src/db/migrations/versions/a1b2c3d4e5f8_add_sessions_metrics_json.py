"""Add sessions.metrics_json for metrics plugin compute() results.

Revision ID: a1b2c3d4e5f8
Revises: e6f7a8b9c0d1
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f8"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("metrics_json", sa.Text(), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("sessions", "metrics_json", schema="core")
