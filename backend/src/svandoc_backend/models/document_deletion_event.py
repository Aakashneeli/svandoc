from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from svandoc_backend.db import Base


class DocumentDeletionEvent(Base):
    __tablename__ = "document_deletion_events"
    __table_args__ = (
        Index("ix_document_deletion_events_document_id", "document_id"),
        Index("ix_document_deletion_events_deleted_at", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    delete_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_by: Mapped[str] = mapped_column(String(64), nullable=False)
    original_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
