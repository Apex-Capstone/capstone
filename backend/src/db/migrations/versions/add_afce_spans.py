"""add_afce_spans

Revision ID: add_afce_spans_001
Revises: dabe018eb7d3
Create Date: 2025-01-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'e0f0eafeb72a'
down_revision: Union[str, None] = 'dabe018eb7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check existing columns in turns table
    turns_columns = [col['name'] for col in inspector.get_columns('turns')]
    
    # Add spans_json and relations_json columns to turns table if they don't exist
    if 'spans_json' not in turns_columns:
        op.add_column('turns', sa.Column('spans_json', sa.Text(), nullable=True))
    if 'relations_json' not in turns_columns:
        op.add_column('turns', sa.Column('relations_json', sa.Text(), nullable=True))
    
    # Check existing columns in feedback table
    feedback_columns = [col['name'] for col in inspector.get_columns('feedback')]
    
    # Update feedback table: add AFCE-structured metrics if they don't exist
    if 'eo_counts_by_dimension' not in feedback_columns:
        op.add_column('feedback', sa.Column('eo_counts_by_dimension', sa.Text(), nullable=True))
    if 'elicitation_counts_by_type' not in feedback_columns:
        op.add_column('feedback', sa.Column('elicitation_counts_by_type', sa.Text(), nullable=True))
    if 'response_counts_by_type' not in feedback_columns:
        op.add_column('feedback', sa.Column('response_counts_by_type', sa.Text(), nullable=True))
    if 'missed_opportunities_by_dimension' not in feedback_columns:
        op.add_column('feedback', sa.Column('missed_opportunities_by_dimension', sa.Text(), nullable=True))
    if 'eo_to_elicitation_links' not in feedback_columns:
        op.add_column('feedback', sa.Column('eo_to_elicitation_links', sa.Text(), nullable=True))
    if 'eo_to_response_links' not in feedback_columns:
        op.add_column('feedback', sa.Column('eo_to_response_links', sa.Text(), nullable=True))
    
    # Note: SQLite doesn't support ALTER COLUMN to change nullable constraints
    # The columns will remain as they are (already nullable in most cases)
    # This is acceptable since we're just stopping computation, not removing the columns


def downgrade() -> None:
    # Remove AFCE-structured metrics
    op.drop_column('feedback', 'eo_to_response_links')
    op.drop_column('feedback', 'eo_to_elicitation_links')
    op.drop_column('feedback', 'missed_opportunities_by_dimension')
    op.drop_column('feedback', 'response_counts_by_type')
    op.drop_column('feedback', 'elicitation_counts_by_type')
    op.drop_column('feedback', 'eo_counts_by_dimension')
    
    # Remove spans columns from turns
    op.drop_column('turns', 'relations_json')
    op.drop_column('turns', 'spans_json')
    
    # Note: We don't revert nullable changes for deprecated columns in downgrade
    # as they may have been nullable before or this is a one-way migration

