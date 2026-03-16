"""Add supporting index for open sessions per user/case.

NOTE: We intentionally do **not** enforce a hard UNIQUE constraint here because
the application supports an explicit "Start New Session" flow via force_new=True
that may legitimately create multiple open sessions for the same (user, case).
Instead, we rely on application-level idempotency for the non-forced path and
use this index only to make lookups efficient.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_ix_sessions_open_001"  # keep <= 32 chars for alembic_version.version_num
down_revision: Union[str, None] = "e0f0eafeb72a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_index(
      "ix_sessions_user_case_open",
      "sessions",
      ["user_id", "case_id", "ended_at"],
      schema="core",
      if_not_exists=True,
  )


def downgrade() -> None:
  op.drop_index("ix_sessions_user_case_open", table_name="sessions", schema="core")

