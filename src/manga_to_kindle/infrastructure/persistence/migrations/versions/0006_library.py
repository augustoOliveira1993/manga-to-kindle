"""Favoritos, preferências, ativos desvinculados e journal de exclusão F008."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from manga_to_kindle.domain.library import normalize_search_text

revision = "0006_library"
down_revision = "0005_export_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("manga") as batch:
        batch.add_column(
            sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("search_key", sa.Text(), nullable=False, server_default="")
        )
    with op.batch_alter_table("chapter") as batch:
        batch.add_column(
            sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("search_key", sa.Text(), nullable=False, server_default="")
        )
    with op.batch_alter_table("image_import_job") as batch:
        batch.add_column(sa.Column("manga_title_snapshot", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("chapter_title_snapshot", sa.String(length=512), nullable=True))

    bind = op.get_bind()
    manga_rows = bind.execute(sa.text("SELECT id, title, author FROM manga")).all()
    if manga_rows:
        bind.execute(
            sa.text("UPDATE manga SET search_key = :search_key WHERE id = :manga_id"),
            [
            {
                "manga_id": manga_id,
                "search_key": normalize_search_text(f"{title} {author or ''}"),
            }
            for manga_id, title, author in manga_rows
            ],
        )
    chapter_rows = bind.execute(
        sa.text("SELECT id, title, number, volume FROM chapter")
    ).all()
    if chapter_rows:
        bind.execute(
            sa.text("UPDATE chapter SET search_key = :search_key WHERE id = :chapter_id"),
            [
            {
                "chapter_id": chapter_id,
                "search_key": normalize_search_text(
                    f"{title or ''} {number or ''} {volume or ''}"
                ),
            }
            for chapter_id, title, number, volume in chapter_rows
            ],
        )
    bind.execute(
        sa.text(
            "UPDATE image_import_job SET "
            "manga_title_snapshot = (SELECT title FROM manga WHERE manga.id = "
            "image_import_job.target_manga_id), "
            "chapter_title_snapshot = (SELECT coalesce(chapter.title, chapter.number) "
            "FROM chapter WHERE chapter.id = image_import_job.target_chapter_id)"
        )
    )

    op.create_index("ix_manga_title_nocase", "manga", ["title"])
    op.create_index("ix_manga_favorite_updated", "manga", ["favorite", "updated_at"])
    op.create_index(
        "ix_chapter_manga_favorite_position", "chapter", ["manga_id", "favorite", "position"]
    )

    op.create_table(
        "library_preference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("favorite_only", sa.Boolean(), nullable=False),
        sa.Column("availability_filter", sa.String(length=32), nullable=True),
        sa.Column("download_state", sa.String(length=24), nullable=True),
        sa.Column("export_state", sa.String(length=24), nullable=True),
        sa.Column("sort_order", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_library_preference_singleton"),
        sa.CheckConstraint(
            "availability_filter IS NULL OR availability_filter IN "
            "('downloaded', 'partial', 'not_downloaded', 'imported', 'missing', 'altered')",
            name="ck_library_preference_availability",
        ),
        sa.CheckConstraint(
            "sort_order IN ('title', 'activity', 'state', 'chapter')",
            name="ck_library_preference_sort",
        ),
        sa.CheckConstraint(
            "download_state IS NULL OR download_state IN "
            "('queued', 'running', 'paused', 'interrupted', 'succeeded', 'failed', 'cancelled')",
            name="ck_library_preference_download_state",
        ),
        sa.CheckConstraint(
            "export_state IS NULL OR export_state IN "
            "('requested', 'running', 'completed', 'failed', 'cancelled', 'missing', 'altered')",
            name="ck_library_preference_export_state",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "library_asset",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=True),
        sa.Column("managed", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('original', 'processed', 'download', 'export')",
            name="ck_library_asset_category",
        ),
        sa.CheckConstraint(
            "state IN ('unlinked', 'missing', 'changed')", name="ck_library_asset_state"
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_library_asset_size"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path", name="uq_library_asset_path"),
    )
    op.create_table(
        "library_deletion_plan",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('planned', 'running', 'completed', 'partial', 'failed')",
            name="ck_library_deletion_plan_state",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "library_deletion_item",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint("kind IN ('record', 'asset')", name="ck_library_deletion_item_kind"),
        sa.CheckConstraint(
            "state IN ('pending', 'deleted', 'preserved', 'missing', 'changed', 'failed')",
            name="ck_library_deletion_item_state",
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0", name="ck_library_deletion_item_size"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["library_deletion_plan.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "kind", "target_id", name="uq_library_deletion_item_target"),
    )


def downgrade() -> None:
    op.drop_table("library_deletion_item")
    op.drop_table("library_deletion_plan")
    op.drop_table("library_asset")
    op.drop_table("library_preference")
    op.drop_index("ix_chapter_manga_favorite_position", table_name="chapter")
    op.drop_index("ix_manga_favorite_updated", table_name="manga")
    op.drop_index("ix_manga_title_nocase", table_name="manga")
    with op.batch_alter_table("image_import_job") as batch:
        batch.drop_column("chapter_title_snapshot")
        batch.drop_column("manga_title_snapshot")
    with op.batch_alter_table("chapter") as batch:
        batch.drop_column("search_key")
        batch.drop_column("favorite")
    with op.batch_alter_table("manga") as batch:
        batch.drop_column("search_key")
        batch.drop_column("favorite")
