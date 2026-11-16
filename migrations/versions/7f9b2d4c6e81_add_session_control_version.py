"""add session control version

Revision ID: 7f9b2d4c6e81
Revises: 5e7a9c1d3b42
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f9b2d4c6e81"
down_revision: str | None = "5e7a9c1d3b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "control_version",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "control_version")
