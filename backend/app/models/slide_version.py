import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.slide import Slide


class SlideVersion(Base):
    __tablename__ = "slide_version"

    id: Mapped[uuid.UUID] = uuid_pk()
    slide_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slide.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    origin: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # manual|ai_generate|ai_edit|user_save|user_checkpoint|restore
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ir: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    skeleton: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    scene: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    scene_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    slide: Mapped["Slide"] = relationship("Slide", back_populates="versions")

    __table_args__ = (UniqueConstraint("slide_id", "seq", name="uq_slide_version_slide_seq"),)
