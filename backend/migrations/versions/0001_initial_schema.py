"""0001_initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-10-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. deck table
    op.create_table(
        "deck",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 2. asset table (id is sha1 string)
    op.create_table(
        "asset",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deck.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_asset_deck_id", "asset", ["deck_id"])

    # 3. resource table
    op.create_table(
        "resource",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deck.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_resource_deck_id", "resource", ["deck_id"])

    # 4. resource_image table
    op.create_table(
        "resource_image",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resource.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id", sa.String(64), sa.ForeignKey("asset.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("locator", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_resource_image_resource_id", "resource_image", ["resource_id"])

    # 5. plan table
    op.create_table(
        "plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deck.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(50), nullable=False, server_default="ai"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_plan_deck_id", "plan", ["deck_id"])

    # 6. slide table
    op.create_table(
        "slide",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deck.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("plan_key", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="ready"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_scene", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("draft_rev", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draft_hash", sa.String(64), nullable=True),
        sa.Column("draft_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_slide_deck_position", "slide", ["deck_id", "position"])

    # 7. slide_version table
    op.create_table(
        "slide_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "slide_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slide.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("origin", sa.String(50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ir", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("skeleton", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scene", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scene_hash", sa.String(64), nullable=True),
        sa.Column(
            "warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slide_id", "seq", name="uq_slide_version_slide_seq"),
    )
    op.create_index("ix_slide_version_slide_id", "slide_version", ["slide_id"])

    # 8. deck_revision table
    op.create_table(
        "deck_revision",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deck.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("origin", sa.String(50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_deck_revision_deck_id", "deck_revision", ["deck_id"])

    # 9. llm_call table
    op.create_table(
        "llm_call",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("llm_call")
    op.drop_table("deck_revision")
    op.drop_table("slide_version")
    op.drop_table("slide")
    op.drop_table("plan")
    op.drop_table("resource_image")
    op.drop_table("resource")
    op.drop_table("asset")
    op.drop_table("deck")
