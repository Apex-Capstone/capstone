"""add_case_patient_metrics_and_session_freeze

Revision ID: a1b2c3d4e5f6
Revises: 5121f6c9fcdd
Create Date: 2026-03-16

Adds Case patient_model_plugin + metrics_plugins and Session frozen
patient_model_plugin, patient_model_version, metrics_plugins.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5121f6c9fcdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("patient_model_plugin", sa.String(), nullable=True),
        schema="core",
    )
    op.add_column(
        "cases",
        sa.Column("metrics_plugins", sa.Text(), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("patient_model_plugin", sa.String(), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("patient_model_version", sa.String(), nullable=True),
        schema="core",
    )
    op.add_column(
        "sessions",
        sa.Column("metrics_plugins", sa.Text(), nullable=True),
        schema="core",
    )


def downgrade() -> None:
    op.drop_column("sessions", "metrics_plugins", schema="core")
    op.drop_column("sessions", "patient_model_version", schema="core")
    op.drop_column("sessions", "patient_model_plugin", schema="core")
    op.drop_column("cases", "metrics_plugins", schema="core")
    op.drop_column("cases", "patient_model_plugin", schema="core")
