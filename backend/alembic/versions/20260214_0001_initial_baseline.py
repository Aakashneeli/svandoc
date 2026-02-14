"""Initial baseline migration.

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline revision for migration framework bootstrap.
    pass


def downgrade() -> None:
    pass
