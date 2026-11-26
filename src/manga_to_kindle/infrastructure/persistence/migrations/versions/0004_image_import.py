"""Importação de originais e derivados locais sem sobrescrita."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_image_import"
down_revision = "0003_download_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("page") as batch:
        batch.add_column(sa.Column("source_relative_path", sa.Text(), nullable=True))
        batch.add_column(sa.Column("source_sha256", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("source_media_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("source_width", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source_height", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("import_job_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(
            sa.Column(
                "duplicate_content",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    op.create_table(
        "image_import_job",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("target_manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("target_chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("total_images", sa.Integer(), nullable=False),
        sa.Column("completed_images", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('staging', 'succeeded', 'failed', 'cancelled', 'interrupted')",
            name="ck_image_import_job_state",
        ),
        sa.CheckConstraint("total_images >= 0", name="ck_image_import_job_total"),
        sa.CheckConstraint("completed_images >= 0", name="ck_image_import_job_completed"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "processed_page",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("page_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("output_order", sa.Integer(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("output_order >= 0", name="ck_processed_page_order"),
        sa.CheckConstraint("width = 600 AND height = 800", name="ck_processed_page_profile_size"),
        sa.ForeignKeyConstraint(["page_id"], ["page.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "output_order", name="uq_processed_page_order"),
    )


def downgrade() -> None:
    op.drop_table("processed_page")
    op.drop_table("image_import_job")
    with op.batch_alter_table("page") as batch:
        batch.drop_column("duplicate_content")
        batch.drop_column("import_job_id")
        batch.drop_column("source_height")
        batch.drop_column("source_width")
        batch.drop_column("source_media_type")
        batch.drop_column("source_sha256")
        batch.drop_column("source_relative_path")
