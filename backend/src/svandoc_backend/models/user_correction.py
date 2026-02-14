from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from svandoc_backend.db import Base


class UserCorrection(Base):
    __tablename__ = "user_corrections"
    __table_args__ = (
        Index("ix_user_corrections_document_id", "document_id"),
        Index("ix_user_corrections_corrected_at", "corrected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_path: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    new_value: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )
    corrected_by: Mapped[str] = mapped_column(String(64), nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    document = relationship("Document", back_populates="user_corrections")

