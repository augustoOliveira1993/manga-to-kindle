"""Metadados opcionais e associação atômica da versão atual do catálogo."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_catalog_snapshot"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("manga", sa.Column("provider_id", sa.String(length=128), nullable=True))
    op.add_column("manga", sa.Column("author", sa.String(length=512), nullable=True))
    op.add_column("manga", sa.Column("cover_path", sa.Text(), nullable=True))
    op.add_column("manga", sa.Column("language", sa.String(length=64), nullable=True))
    op.add_column(
        "manga",
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("chapter", sa.Column("volume", sa.String(length=64), nullable=True))
    op.add_column("chapter", sa.Column("available", sa.Boolean(), nullable=True))
    op.create_table(
        "catalog_membership",
        sa.Column("manga_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=True),
        sa.CheckConstraint("position >= 0", name="ck_catalog_membership_position"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["manga_id"], ["manga.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("manga_id", "chapter_id"),
        sa.UniqueConstraint("manga_id", "position", name="uq_catalog_manga_position"),
    )
def downgrade() -> None:
    op.drop_table("catalog_membership")
    op.drop_column("chapter", "available")
    op.drop_column("chapter", "volume")
    op.drop_column("manga", "simulated")
    op.drop_column("manga", "language")
    op.drop_column("manga", "cover_path")
    op.drop_column("manga", "author")
    op.drop_column("manga", "provider_id")
