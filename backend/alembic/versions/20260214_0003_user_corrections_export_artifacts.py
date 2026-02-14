"""Add user corrections and export artifacts tables.

Revision ID: 20260214_0003
Revises: 20260214_0002
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260214_0003"
down_revision = "20260214_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_corrections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("field_path", sa.Text(), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("corrected_by", sa.String(length=64), nullable=False),
        sa.Column(
            "corrected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_corrections_document_id", "user_corrections", ["document_id"], unique=False)
    op.create_index("ix_user_corrections_corrected_at", "user_corrections", ["corrected_at"], unique=False)

    op.create_table(
        "export_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("format IN ('csv', 'xlsx', 'json')", name="ck_export_artifacts_format_valid"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_artifacts_document_id", "export_artifacts", ["document_id"], unique=False)
    op.create_index("ix_export_artifacts_created_at", "export_artifacts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_export_artifacts_created_at", table_name="export_artifacts")
    op.drop_index("ix_export_artifacts_document_id", table_name="export_artifacts")
    op.drop_table("export_artifacts")

    op.drop_index("ix_user_corrections_corrected_at", table_name="user_corrections")
    op.drop_index("ix_user_corrections_document_id", table_name="user_corrections")
    op.drop_table("user_corrections")

