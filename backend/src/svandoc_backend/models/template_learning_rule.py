from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from svandoc_backend.db import Base


class TemplateLearningRule(Base):
    __tablename__ = "template_learning_rules"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "template_id",
            "field_path",
            "corrected_value",
            name="uq_template_learning_rules_scope_value",
        ),
        Index("ix_template_learning_rules_template_id", "template_id"),
        Index("ix_template_learning_rules_field_path", "field_path"),
        Index("ix_template_learning_rules_last_seen_at", "last_seen_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    template_id: Mapped[str] = mapped_column(String(36), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False)
    field_path: Mapped[str] = mapped_column(String(256), nullable=False)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
