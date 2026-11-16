"""add ticket lifecycle events

Revision ID: 5e7a9c1d3b42
Revises: 2c4e6a8b1d30
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e7a9c1d3b42"
down_revision: str | None = "2c4e6a8b1d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "after_sales_tickets",
        sa.Column("active_dedup_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_after_sales_tickets_cancelled_by_id_users"),
        "after_sales_tickets",
        "users",
        ["cancelled_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_after_sales_tickets_active_dedup_key"),
        "after_sales_tickets",
        ["active_dedup_key"],
        unique=True,
    )
    op.execute(
        "UPDATE after_sales_tickets "
        "SET active_dedup_key = CONCAT(user_id, ':', order_id, ':', request_type) "
        "WHERE status IN ('pending_approval', 'approved')"
    )

    op.create_table(
        "after_sales_ticket_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('created', 'approved', 'rejected', 'cancelled', 'system_note')",
            name=op.f("ck_after_sales_ticket_events_valid_event_type"),
        ),
        sa.CheckConstraint(
            "actor_type IN ('consumer', 'agent', 'system')",
            name=op.f("ck_after_sales_ticket_events_valid_actor_type"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_after_sales_ticket_events_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["after_sales_tickets.id"],
            name=op.f("fk_after_sales_ticket_events_ticket_id_after_sales_tickets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_after_sales_ticket_events")),
    )
    op.create_index(
        "ix_after_sales_ticket_events_ticket_id_created_at",
        "after_sales_ticket_events",
        ["ticket_id", "created_at"],
        unique=False,
    )
    op.execute(
        "INSERT INTO after_sales_ticket_events "
        "(ticket_id, event_type, from_status, to_status, actor_type, actor_id, note, created_at) "
        "SELECT id, 'created', NULL, 'pending_approval', 'consumer', user_id, "
        "'历史售后工单导入', created_at FROM after_sales_tickets"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_after_sales_ticket_events_ticket_id_created_at",
        table_name="after_sales_ticket_events",
    )
    op.drop_table("after_sales_ticket_events")
    op.drop_index(
        op.f("ix_after_sales_tickets_active_dedup_key"),
        table_name="after_sales_tickets",
    )
    op.drop_constraint(
        op.f("fk_after_sales_tickets_cancelled_by_id_users"),
        "after_sales_tickets",
        type_="foreignkey",
    )
    op.drop_column("after_sales_tickets", "cancelled_by_id")
    op.drop_column("after_sales_tickets", "cancelled_at")
    op.drop_column("after_sales_tickets", "active_dedup_key")
