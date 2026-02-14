from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from svandoc_backend.db import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("page_count > 0", name="ck_documents_page_count_positive"),
        UniqueConstraint("checksum", name="uq_documents_checksum"),
        Index("ix_documents_team_id", "team_id"),
        Index("ix_documents_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    jobs = relationship("Job", back_populates="document", cascade="all, delete-orphan")
    extraction_result = relationship(
        "ExtractionResult",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    user_corrections = relationship(
        "UserCorrection",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    export_artifacts = relationship(
        "ExportArtifact",
        back_populates="document",
        cascade="all, delete-orphan",
    )
