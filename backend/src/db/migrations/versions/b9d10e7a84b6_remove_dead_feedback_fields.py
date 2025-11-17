"""remove_dead_feedback_fields

Revision ID: b9d10e7a84b6
Revises: e0f0eafeb72a
Create Date: 2025-01-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9d10e7a84b6'
down_revision: Union[str, None] = 'e0f0eafeb72a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove dead code fields from feedback table
    op.drop_column('feedback', 'tone_summary')
    op.drop_column('feedback', 'interruptions')
    op.drop_column('feedback', 'reflections_interpretations')
    op.drop_column('feedback', 'prohibited_behaviors')
    op.drop_column('feedback', 'deescalation_strategies')


def downgrade() -> None:
    # Restore removed columns for rollback
    op.add_column('feedback', sa.Column('tone_summary', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('interruptions', sa.Integer(), nullable=True))
    op.add_column('feedback', sa.Column('reflections_interpretations', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('prohibited_behaviors', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('deescalation_strategies', sa.Text(), nullable=True))

