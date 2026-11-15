"""add after-sales tickets

Revision ID: 4f8c2d7a1b90
Revises: 0eebbeffd084
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f8c2d7a1b90"
down_revision: str | None = "0eebbeffd084"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "after_sales_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_no", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("issue_description", sa.Text(), nullable=False),
        sa.Column("policy_citations_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending_approval",
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "request_type IN ('return', 'exchange')",
            name=op.f("ck_after_sales_tickets_valid_request_type"),
        ),
        sa.CheckConstraint(
            "status IN ('pending_approval', 'approved', 'rejected', 'cancelled')",
            name=op.f("ck_after_sales_tickets_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_after_sales_tickets_order_id_orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_after_sales_tickets_reviewer_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name=op.f("fk_after_sales_tickets_session_id_chat_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_after_sales_tickets_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_after_sales_tickets")),
        sa.UniqueConstraint("session_id", name="uq_after_sales_tickets_session_id"),
    )
    op.create_index(
        "ix_after_sales_tickets_status_created_at",
        "after_sales_tickets",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_after_sales_tickets_order_id"),
        "after_sales_tickets",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_after_sales_tickets_reviewer_id"),
        "after_sales_tickets",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_after_sales_tickets_ticket_no"),
        "after_sales_tickets",
        ["ticket_no"],
        unique=True,
    )
    op.create_index(
        op.f("ix_after_sales_tickets_user_id"),
        "after_sales_tickets",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_after_sales_tickets_user_id"),
        table_name="after_sales_tickets",
    )
    op.drop_index(
        op.f("ix_after_sales_tickets_ticket_no"),
        table_name="after_sales_tickets",
    )
    op.drop_index(
        op.f("ix_after_sales_tickets_reviewer_id"),
        table_name="after_sales_tickets",
    )
    op.drop_index(
        op.f("ix_after_sales_tickets_order_id"),
        table_name="after_sales_tickets",
    )
    op.drop_index(
        "ix_after_sales_tickets_status_created_at",
        table_name="after_sales_tickets",
    )
    op.drop_table("after_sales_tickets")
