from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from svandoc_backend.db import Base


class XeroSyncLog(Base):
    __tablename__ = "xero_sync_logs"
    __table_args__ = (
        CheckConstraint(
            "sync_status IN ('synced', 'retrying', 'failed')",
            name="ck_xero_sync_logs_status_valid",
        ),
        Index("ix_xero_sync_logs_document_id", "document_id"),
        Index("ix_xero_sync_logs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sync_status: Mapped[str] = mapped_column(String(16), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
