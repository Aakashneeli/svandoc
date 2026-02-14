from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from svandoc_backend.db import Base


class ExtractionResult(Base):
    __tablename__ = "extraction_results"
    __table_args__ = (
        CheckConstraint("doc_type IN ('invoice', 'receipt')", name="ck_extraction_results_doc_type_valid"),
        UniqueConstraint("document_id", name="uq_extraction_results_document_id"),
        Index("ix_extraction_results_doc_type", "doc_type"),
        Index("ix_extraction_results_review_required", "is_review_required"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_ocr_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_map: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    document = relationship("Document", back_populates="extraction_result")
