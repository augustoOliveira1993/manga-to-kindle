"""Permite registrar artefatos MOBI criados pela CLI KCC local verificada."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_mobi_export_artifacts"
down_revision = "0010_catalog_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("export_artifact") as batch:
        batch.drop_constraint("ck_export_artifact_format", type_="check")
        batch.create_check_constraint(
            "ck_export_artifact_format",
            "format IN ('epub', 'cbz', 'mobi')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    mobi_artifact_count = bind.scalar(
        sa.text("SELECT count(*) FROM export_artifact WHERE format = 'mobi'")
    )
    if mobi_artifact_count:
        raise RuntimeError("MOBI export records must be removed before this migration is reversed.")
    with op.batch_alter_table("export_artifact") as batch:
        batch.drop_constraint("ck_export_artifact_format", type_="check")
        batch.create_check_constraint(
            "ck_export_artifact_format",
            "format IN ('epub', 'cbz')",
        )
