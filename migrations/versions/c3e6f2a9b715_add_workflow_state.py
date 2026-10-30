"""add workflow state

Revision ID: c3e6f2a9b715
Revises: 7a31c4d8e2f9
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e6f2a9b715"
down_revision: str | None = "7a31c4d8e2f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "workflow_state",
            sa.String(length=32),
            server_default="collecting_info",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        "workflow_state IN "
        "('collecting_info', 'checking_order', 'checking_policy', "
        "'answer_ready', 'need_human', 'resolved')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        type_="check",
    )
    op.drop_column("chat_sessions", "workflow_state")
