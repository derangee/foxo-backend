"""add version column to products for optimistic locking

Revision ID: 2b9ef65dd56e
Revises: 0c2025fa15ed
Create Date: 2026-07-23 14:23:18.835000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b9ef65dd56e"
down_revision: str | Sequence[str] | None = "0c2025fa15ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the optimistic-lock version counter, defaulting existing rows to 1."""
    op.add_column(
        "products",
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the version counter."""
    op.drop_column("products", "version")
