"""allow quickbooks format in export artifacts

Revision ID: 20260215_0009
Revises: 20260215_0008
Create Date: 2026-02-15 01:20:00
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260215_0009"
down_revision = "20260215_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox', 'quickbooks')",
        )


def downgrade() -> None:
    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox')",
        )
