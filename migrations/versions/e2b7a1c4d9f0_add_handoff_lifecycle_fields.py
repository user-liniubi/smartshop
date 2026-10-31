"""Add handoff lifecycle and source fields.

Revision ID: e2b7a1c4d9f0
Revises: c3e6f2a9b715
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2b7a1c4d9f0"
down_revision: str | None = "c3e6f2a9b715"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "handoffs",
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column(
        "handoffs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "handoffs",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_handoffs_valid_source"),
        "handoffs",
        "source IN ('user', 'ai', 'rule')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_handoffs_valid_source"),
        "handoffs",
        type_="check",
    )
    op.drop_column("handoffs", "closed_at")
    op.drop_column("handoffs", "claimed_at")
    op.drop_column("handoffs", "source")
