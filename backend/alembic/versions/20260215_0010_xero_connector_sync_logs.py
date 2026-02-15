"""add xero connector sync logs and export format

Revision ID: 20260215_0010
Revises: 20260215_0009
Create Date: 2026-02-15 01:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260215_0010"
down_revision = "20260215_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox', 'quickbooks', 'xero')",
        )

    op.create_table(
        "xero_sync_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("sync_status", sa.String(length=16), nullable=False),
        sa.Column("external_reference", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sync_status IN ('synced', 'retrying', 'failed')",
            name="ck_xero_sync_logs_status_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_xero_sync_logs_document_id", "xero_sync_logs", ["document_id"], unique=False)
    op.create_index("ix_xero_sync_logs_created_at", "xero_sync_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_xero_sync_logs_created_at", table_name="xero_sync_logs")
    op.drop_index("ix_xero_sync_logs_document_id", table_name="xero_sync_logs")
    op.drop_table("xero_sync_logs")

    with op.batch_alter_table("export_artifacts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_export_artifacts_format_valid", type_="check")
        batch_op.create_check_constraint(
            "ck_export_artifacts_format_valid",
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox', 'quickbooks')",
        )
