import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.deck import Deck


class Resource(Base, TimestampMixin):
    __tablename__ = "resource"

    id: Mapped[uuid.UUID] = uuid_pk()
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deck.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf|docx|pptx|md|image|text
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded", nullable=False
    )  # uploaded|parsing|parsed|failed
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    deck: Mapped["Deck"] = relationship("Deck", back_populates="resources")
    images: Mapped[list["ResourceImage"]] = relationship(
        "ResourceImage", back_populates="resource", cascade="all, delete-orphan"
    )


class ResourceImage(Base):
    __tablename__ = "resource_image"

    id: Mapped[uuid.UUID] = uuid_pk()
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resource.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resource: Mapped["Resource"] = relationship("Resource", back_populates="images")
    asset: Mapped["Asset"] = relationship("Asset")
