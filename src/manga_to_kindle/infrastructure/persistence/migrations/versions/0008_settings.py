"""Preferências gerais, política de cache e manifesto F011."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_settings"
down_revision = "0007_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("selected_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("download_concurrency", sa.Integer(), nullable=False),
        sa.Column("download_directory", sa.Text(), nullable=False),
        sa.Column("export_directory", sa.Text(), nullable=False),
        sa.Column("cache_directory", sa.Text(), nullable=False),
        sa.Column("cache_limit_bytes", sa.BigInteger(), nullable=False),
        sa.Column("cache_retention_days", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_application_preferences_singleton"),
        sa.CheckConstraint(
            "download_concurrency BETWEEN 1 AND 2",
            name="ck_application_preferences_download_concurrency",
        ),
        sa.CheckConstraint(
            "cache_limit_bytes BETWEEN 104857600 AND 21474836480",
            name="ck_application_preferences_cache_limit",
        ),
        sa.CheckConstraint(
            "cache_retention_days BETWEEN 1 AND 365",
            name="ck_application_preferences_cache_retention",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cache_manifest",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("in_use", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(sha256) = 64", name="ck_cache_manifest_sha256"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_cache_manifest_size"),
        sa.CheckConstraint(
            "category IN ('preview', 'thumbnail')",
            name="ck_cache_manifest_category",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path", "relative_path", name="uq_cache_manifest_path"),
    )
    op.create_index(
        "ix_cache_manifest_root_accessed",
        "cache_manifest",
        ["root_path", "last_accessed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cache_manifest_root_accessed", table_name="cache_manifest")
    op.drop_table("cache_manifest")
    op.drop_table("application_preferences")
