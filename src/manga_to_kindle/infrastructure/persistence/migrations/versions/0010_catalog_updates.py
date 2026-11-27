"""Identidade estável e estado local de atualizações de catálogo F010."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_catalog_updates"
down_revision = "0009_profile_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chapter", sa.Column("source_chapter_id", sa.String(length=512)))
    op.create_index(
        "uq_chapter_manga_source_id",
        "chapter",
        ["manga_id", "source_chapter_id"],
        unique=True,
        sqlite_where=sa.text("source_chapter_id IS NOT NULL"),
    )
    op.create_table(
        "update_preference",
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("enabled IN (0, 1)", name="ck_update_preference_enabled"),
        sa.CheckConstraint(
            "interval_seconds IS NULL OR interval_seconds >= 1",
            name="ck_update_preference_interval",
        ),
        sa.CheckConstraint(
            "enabled = 0 OR interval_seconds IS NOT NULL",
            name="ck_update_preference_enabled_interval",
        ),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("manga_id"),
    )
    op.create_table(
        "update_check",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("chapter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_chapter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("safe_error_code", sa.String(length=64), nullable=True),
        sa.Column("retry_after_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_fingerprint", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'rate_limited', 'cancelled', 'unsupported')",
            name="ck_update_check_status",
        ),
        sa.CheckConstraint("chapter_count >= 0", name="ck_update_check_chapter_count"),
        sa.CheckConstraint(
            "new_chapter_count >= 0 AND new_chapter_count <= chapter_count",
            name="ck_update_check_new_count",
        ),
        sa.CheckConstraint(
            "policy_fingerprint IS NULL OR length(policy_fingerprint) = 64",
            name="ck_update_check_policy_fingerprint",
        ),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_update_check_manga_started", "update_check", ["manga_id", "started_at"])
    op.create_table(
        "chapter_notice",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("source_chapter_id", sa.String(length=512), nullable=False),
        sa.Column("chapter_title_snapshot", sa.String(length=512), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("check_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["check_id"], ["update_check.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "manga_id",
            "provider_id",
            "source_chapter_id",
            name="uq_chapter_notice_stable_identity",
        ),
    )
    op.create_index("ix_chapter_notice_manga_read", "chapter_notice", ["manga_id", "read_at"])


def downgrade() -> None:
    op.drop_index("ix_chapter_notice_manga_read", table_name="chapter_notice")
    op.drop_table("chapter_notice")
    op.drop_index("ix_update_check_manga_started", table_name="update_check")
    op.drop_table("update_check")
    op.drop_table("update_preference")
    op.drop_index("uq_chapter_manga_source_id", table_name="chapter")
    op.drop_column("chapter", "source_chapter_id")
