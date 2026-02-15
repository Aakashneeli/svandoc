"""Add document deletion audit table for retention hard-delete job.

Revision ID: 20260215_0005
Revises: 20260214_0004
Create Date: 2026-02-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260215_0005"
down_revision = "20260214_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_deletion_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("delete_reason", sa.String(length=64), nullable=False),
        sa.Column("deleted_by", sa.String(length=64), nullable=False),
        sa.Column("original_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_deletion_events_document_id",
        "document_deletion_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_deletion_events_deleted_at",
        "document_deletion_events",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_deletion_events_deleted_at", table_name="document_deletion_events")
    op.drop_index("ix_document_deletion_events_document_id", table_name="document_deletion_events")
    op.drop_table("document_deletion_events")
