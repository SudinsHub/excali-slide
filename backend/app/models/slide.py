import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.deck import Deck
    from app.models.slide_version import SlideVersion


class Slide(Base, TimestampMixin):
    __tablename__ = "slide"

    id: Mapped[uuid.UUID] = uuid_pk()
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deck.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="ready", nullable=False
    )  # queued|generating|ready|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    draft_scene: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    draft_rev: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draft_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draft_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deck: Mapped["Deck"] = relationship("Deck", back_populates="slides")
    versions: Mapped[list["SlideVersion"]] = relationship(
        "SlideVersion",
        back_populates="slide",
        cascade="all, delete-orphan",
        order_by="SlideVersion.seq",
    )

    __table_args__ = (Index("ix_slide_deck_position", "deck_id", "position"),)
