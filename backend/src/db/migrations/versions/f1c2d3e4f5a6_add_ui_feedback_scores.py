"""add_ui_feedback_scores

Revision ID: f1c2d3e4f5a6
Revises: b9d10e7a84b6
Create Date: 2026-03-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1c2d3e4f5a6'
down_revision: Union[str, None] = 'b9d10e7a84b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedback', sa.Column('clinical_reasoning_score', sa.Float(), nullable=True), schema='core')
    op.add_column('feedback', sa.Column('professionalism_score', sa.Float(), nullable=True), schema='core')


def downgrade() -> None:
    op.drop_column('feedback', 'professionalism_score', schema='core')
    op.drop_column('feedback', 'clinical_reasoning_score', schema='core')
