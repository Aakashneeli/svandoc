"""Add cloud connector export formats and delivery status.

Revision ID: 20260215_0007
Revises: 20260215_0006
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260215_0007"
down_revision = "20260215_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.add_column(
            sa.Column(
                "delivery_status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'completed'"),
            )
        )
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox')",
        )
        batch_op.create_check_constraint(
            "ck_export_artifacts_delivery_status_valid",
            "delivery_status IN ('pending', 'completed', 'failed')",
        )


def downgrade() -> None:
    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_delivery_status_valid", type_="check")
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.drop_column("delivery_status")
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets')",
        )

