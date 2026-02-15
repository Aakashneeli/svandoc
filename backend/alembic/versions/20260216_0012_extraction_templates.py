"""add extraction templates table

Revision ID: 20260216_0012
Revises: 20260216_0011
Create Date: 2026-02-16 03:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260216_0012"
down_revision = "20260216_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("schema_definition", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("field_mapping", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_templates_team_id", "extraction_templates", ["team_id"], unique=False)
    op.create_index("ix_extraction_templates_doc_type", "extraction_templates", ["doc_type"], unique=False)
    op.create_index("ix_extraction_templates_created_at", "extraction_templates", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_extraction_templates_created_at", table_name="extraction_templates")
    op.drop_index("ix_extraction_templates_doc_type", table_name="extraction_templates")
    op.drop_index("ix_extraction_templates_team_id", table_name="extraction_templates")
    op.drop_table("extraction_templates")
