import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.deck_revision import DeckRevision
    from app.models.resource import Resource
    from app.models.slide import Slide


class Deck(Base, TimestampMixin):
    __tablename__ = "deck"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    current_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    slides: Mapped[list["Slide"]] = relationship(
        "Slide",
        back_populates="deck",
        cascade="all, delete-orphan",
        order_by="Slide.position",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="deck",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["Resource"]] = relationship(
        "Resource",
        back_populates="deck",
        cascade="all, delete-orphan",
    )
    revisions: Mapped[list["DeckRevision"]] = relationship(
        "DeckRevision",
        back_populates="deck",
        cascade="all, delete-orphan",
    )
