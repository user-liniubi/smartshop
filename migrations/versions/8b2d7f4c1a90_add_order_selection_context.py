"""add order selection context

Revision ID: 8b2d7f4c1a90
Revises: 4f8c2d7a1b90
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b2d7f4c1a90"
down_revision: str | None = "4f8c2d7a1b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("selected_order_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column(
            "candidate_order_ids_json",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE chat_sessions SET candidate_order_ids_json = JSON_ARRAY() "
        "WHERE candidate_order_ids_json IS NULL"
    )
    op.alter_column(
        "chat_sessions",
        "candidate_order_ids_json",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.add_column(
        "chat_sessions",
        sa.Column(
            "order_selection_state",
            sa.String(length=24),
            server_default="none",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_chat_sessions_selected_order_id_orders"),
        "chat_sessions",
        "orders",
        ["selected_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_chat_sessions_selected_order_id"),
        "chat_sessions",
        ["selected_order_id"],
        unique=False,
    )
    op.drop_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        "workflow_state IN "
        "('collecting_info', 'awaiting_order_selection', 'checking_order', "
        "'checking_policy', 'answer_ready', 'need_human', 'resolved')",
    )
    op.create_check_constraint(
        op.f("ck_chat_sessions_valid_order_selection_state"),
        "chat_sessions",
        "order_selection_state IN ('none', 'awaiting_selection', 'selected')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_chat_sessions_valid_order_selection_state"),
        "chat_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_chat_sessions_valid_workflow_state"),
        "chat_sessions",
        "workflow_state IN "
        "('collecting_info', 'checking_order', 'checking_policy', "
        "'answer_ready', 'need_human', 'resolved')",
    )
    op.drop_index(
        op.f("ix_chat_sessions_selected_order_id"),
        table_name="chat_sessions",
    )
    op.drop_constraint(
        op.f("fk_chat_sessions_selected_order_id_orders"),
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "order_selection_state")
    op.drop_column("chat_sessions", "candidate_order_ids_json")
    op.drop_column("chat_sessions", "selected_order_id")
