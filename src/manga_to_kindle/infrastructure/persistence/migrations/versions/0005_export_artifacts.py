"""Metadados de execução e artefatos publicados pela exportação F007."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_export_artifacts"
down_revision = "0004_image_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("export") as batch:
        batch.add_column(sa.Column("error_code", sa.String(length=64), nullable=True))

    op.create_table(
        "export_artifact",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("export_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("package_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("chapter_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_export_artifact_position"),
        sa.CheckConstraint("format IN ('epub', 'cbz')", name="ck_export_artifact_format"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_export_artifact_sha256"),
        sa.CheckConstraint("size_bytes > 0", name="ck_export_artifact_size"),
        sa.ForeignKeyConstraint(["export_id"], ["export.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("export_id", "position", name="uq_export_artifact_position"),
        sa.UniqueConstraint("export_id", "package_id", name="uq_export_artifact_package"),
    )


def downgrade() -> None:
    op.drop_table("export_artifact")
    with op.batch_alter_table("export") as batch:
        batch.drop_column("error_code")
