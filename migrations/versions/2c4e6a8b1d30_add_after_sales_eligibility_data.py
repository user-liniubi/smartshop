"""add after-sales eligibility data

Revision ID: 2c4e6a8b1d30
Revises: 8b2d7f4c1a90
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c4e6a8b1d30"
down_revision: str | None = "8b2d7f4c1a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "paid_amount",
            sa.Numeric(precision=12, scale=2),
            server_default="0.00",
            nullable=False,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "shipping_amount",
            sa.Numeric(precision=12, scale=2),
            server_default="0.00",
            nullable=False,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="CNY",
            nullable=False,
        ),
    )
    op.execute("UPDATE orders SET delivered_at = created_at WHERE status = 'delivered'")
    op.execute(
        "UPDATE orders SET paid_amount = CASE "
        "WHEN product_id IN (SELECT id FROM products WHERE name LIKE '%耳机%') THEN 899.00 "
        "WHEN product_id IN (SELECT id FROM products WHERE name LIKE '%键盘%') THEN 499.00 "
        "WHEN product_id IN (SELECT id FROM products WHERE name LIKE '%显示器%') THEN 1599.00 "
        "WHEN product_id IN (SELECT id FROM products WHERE name LIKE '%笔记本%') THEN 5299.00 "
        "WHEN product_id IN (SELECT id FROM products WHERE name LIKE '%鼠标%') THEN 199.00 "
        "ELSE paid_amount END"
    )

    op.add_column(
        "after_sales_tickets",
        sa.Column("eligibility_result", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column("eligibility_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column(
            "refund_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="CNY",
            nullable=False,
        ),
    )
    op.add_column(
        "after_sales_tickets",
        sa.Column("rule_version", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_after_sales_tickets_valid_eligibility_result"),
        "after_sales_tickets",
        "eligibility_result IS NULL OR "
        "eligibility_result IN ('eligible', 'need_human_review', 'not_eligible')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_after_sales_tickets_valid_eligibility_result"),
        "after_sales_tickets",
        type_="check",
    )
    op.drop_column("after_sales_tickets", "rule_version")
    op.drop_column("after_sales_tickets", "currency")
    op.drop_column("after_sales_tickets", "refund_amount")
    op.drop_column("after_sales_tickets", "eligibility_reason")
    op.drop_column("after_sales_tickets", "eligibility_result")
    op.drop_column("orders", "currency")
    op.drop_column("orders", "shipping_amount")
    op.drop_column("orders", "paid_amount")
    op.drop_column("orders", "delivered_at")
