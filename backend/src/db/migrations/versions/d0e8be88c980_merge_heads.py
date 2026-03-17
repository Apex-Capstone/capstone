"""merge_heads

Revision ID: d0e8be88c980
Revises: f1c2d3e4f5a6, add_unique_open_session_index_001
Create Date: 2026-03-16 19:22:16.522119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e8be88c980'
down_revision: Union[str, None] = ('f1c2d3e4f5a6', 'add_ix_sessions_open_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

