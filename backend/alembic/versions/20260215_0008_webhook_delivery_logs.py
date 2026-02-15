"""add webhook delivery logs

Revision ID: 20260215_0008
Revises: 20260215_0007
Create Date: 2026-02-15 00:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260215_0008"
down_revision = "20260215_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "delivery_status IN ('delivered', 'failed')",
            name="ck_webhook_delivery_logs_status_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_delivery_logs_event_type",
        "webhook_delivery_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_webhook_delivery_logs_created_at",
        "webhook_delivery_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_logs_created_at", table_name="webhook_delivery_logs")
    op.drop_index("ix_webhook_delivery_logs_event_type", table_name="webhook_delivery_logs")
    op.drop_table("webhook_delivery_logs")
