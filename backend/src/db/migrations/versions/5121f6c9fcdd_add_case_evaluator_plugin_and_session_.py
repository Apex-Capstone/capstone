"""add_case_evaluator_plugin_and_session_evaluator_fields

Revision ID: 5121f6c9fcdd
Revises: d0e8be88c980
Create Date: 2026-03-16 19:23:26.372798

Only adds new columns; tables already exist in core schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5121f6c9fcdd"
down_revision: Union[str, None] = "d0e8be88c980"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("evaluator_plugin", sa.String(), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("evaluator_plugin", sa.String(), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("evaluator_version", sa.String(), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("sessions", "evaluator_version", schema="core")
    op.drop_column("sessions", "evaluator_plugin", schema="core")
    op.drop_column("cases", "evaluator_plugin", schema="core")
