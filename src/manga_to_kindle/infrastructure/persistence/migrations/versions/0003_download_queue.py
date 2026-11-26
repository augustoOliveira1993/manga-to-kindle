"""Fila de download, resultados de página e interrupção recuperável."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_download_queue"
down_revision = "0002_catalog_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("download_job") as batch:
        batch.drop_constraint("ck_download_job_state", type_="check")
        batch.create_check_constraint(
            "ck_download_job_state",
            "state IN ('queued', 'running', 'paused', 'interrupted', "
            "'succeeded', 'failed', 'cancelled')",
        )
        batch.add_column(sa.Column("provider_id", sa.String(length=128), nullable=True))
        batch.add_column(
            sa.Column(
                "policy_snapshot",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.add_column(sa.Column("error_code", sa.String(length=64), nullable=True))

    op.create_table(
        "download_chapter",
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("page_total", sa.Integer(), nullable=True),
        sa.Column("page_completed", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_download_chapter_position"),
        sa.CheckConstraint(
            "page_total IS NULL OR (page_total >= 0 AND page_completed <= page_total)",
            name="ck_download_chapter_progress",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["download_job.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("job_id", "chapter_id"),
        sa.UniqueConstraint("job_id", "position", name="uq_download_chapter_position"),
    )
    op.create_table(
        "download_page",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chapter_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("provider_page_id", sa.String(length=512), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("original_path", sa.Text(), nullable=True),
        sa.Column("temporary_path", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("content_validator", sa.String(length=512), nullable=True),
        sa.Column("duplicate_content", sa.Boolean(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_download_page_position"),
        sa.CheckConstraint("attempts >= 0", name="ck_download_page_attempts"),
        sa.CheckConstraint("byte_size IS NULL OR byte_size >= 0", name="ck_download_page_size"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'staging', 'waiting_retry', "
            "'interrupted', 'complete', 'failed')",
            name="ck_download_page_state",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapter.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["download_job.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id", "chapter_id", "provider_page_id", name="uq_download_page_identity"
        ),
        sa.UniqueConstraint("job_id", "chapter_id", "position", name="uq_download_page_position"),
    )


def downgrade() -> None:
    op.drop_table("download_page")
    op.drop_table("download_chapter")
    with op.batch_alter_table("download_job") as batch:
        batch.drop_column("error_code")
        batch.drop_column("policy_snapshot")
        batch.drop_column("provider_id")
        batch.drop_constraint("ck_download_job_state", type_="check")
        batch.create_check_constraint(
            "ck_download_job_state",
            "state IN ('queued', 'running', 'paused', 'succeeded', 'failed', 'cancelled')",
        )
