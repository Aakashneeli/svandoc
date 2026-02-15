"""add template learning rules table

Revision ID: 20260216_0013
Revises: 20260216_0012
Create Date: 2026-02-16 04:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260216_0013"
down_revision = "20260216_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "template_learning_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("field_path", sa.String(length=256), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("correction_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "template_id",
            "field_path",
            "corrected_value",
            name="uq_template_learning_rules_scope_value",
        ),
    )
    op.create_index(
        "ix_template_learning_rules_template_id",
        "template_learning_rules",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "ix_template_learning_rules_field_path",
        "template_learning_rules",
        ["field_path"],
        unique=False,
    )
    op.create_index(
        "ix_template_learning_rules_last_seen_at",
        "template_learning_rules",
        ["last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_template_learning_rules_last_seen_at", table_name="template_learning_rules")
    op.drop_index("ix_template_learning_rules_field_path", table_name="template_learning_rules")
    op.drop_index("ix_template_learning_rules_template_id", table_name="template_learning_rules")
    op.drop_table("template_learning_rules")
