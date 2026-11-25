"""Schema inicial da biblioteca local."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manga",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_ref", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_manga_title"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "device_profile",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_device_profile_name"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chapter",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("number", sa.String(length=64), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_chapter_position"),
        sa.CheckConstraint(
            "length(trim(coalesce(title, ''))) > 0 OR number IS NOT NULL",
            name="ck_chapter_display_value",
        ),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manga_id", "position", name="uq_chapter_manga_position"),
    )
    op.create_table(
        "page",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_page_position"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "position", name="uq_page_chapter_position"),
    )
    op.create_table(
        "download_job",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(manga_id IS NOT NULL AND chapter_id IS NULL) OR "
            "(manga_id IS NULL AND chapter_id IS NOT NULL)",
            name="ck_download_job_single_target",
        ),
        sa.CheckConstraint("progress >= 0", name="ck_download_job_progress_nonnegative"),
        sa.CheckConstraint(
            "total IS NULL OR (total >= 0 AND progress <= total)",
            name="ck_download_job_progress_total",
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'paused', 'succeeded', 'failed', 'cancelled')",
            name="ck_download_job_state",
        ),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "export",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(destination)) > 0", name="ck_export_destination"),
        sa.CheckConstraint(
            "state IN ('requested', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_export_state",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "export_chapter",
        sa.Column("export_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_export_chapter_position"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["export_id"], ["export.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("export_id", "chapter_id"),
        sa.UniqueConstraint("export_id", "position", name="uq_export_chapter_position"),
    )


def downgrade() -> None:
    op.drop_table("export_chapter")
    op.drop_table("export")
    op.drop_table("download_job")
    op.drop_table("page")
    op.drop_table("chapter")
    op.drop_table("device_profile")
    op.drop_table("manga")
