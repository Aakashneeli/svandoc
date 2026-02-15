from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from svandoc_backend.db import Base


class ExtractionTemplate(Base):
    __tablename__ = "extraction_templates"
    __table_args__ = (
        Index("ix_extraction_templates_team_id", "team_id"),
        Index("ix_extraction_templates_doc_type", "doc_type"),
        Index("ix_extraction_templates_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False)
    schema_definition: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    field_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("1"))
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
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
