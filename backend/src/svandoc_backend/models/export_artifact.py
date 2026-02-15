from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from svandoc_backend.db import Base


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    __table_args__ = (
        CheckConstraint(
            "format IN ('csv', 'xlsx', 'json', 'gsheets', 'gdrive', 'onedrive', 'dropbox', 'quickbooks', 'xero')",
            name="ck_export_artifacts_format_valid",
        ),
        CheckConstraint(
            "delivery_status IN ('pending', 'completed', 'failed')",
            name="ck_export_artifacts_delivery_status_valid",
        ),
        Index("ix_export_artifacts_document_id", "document_id"),
        Index("ix_export_artifacts_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'completed'"))
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    document = relationship("Document", back_populates="export_artifacts")
