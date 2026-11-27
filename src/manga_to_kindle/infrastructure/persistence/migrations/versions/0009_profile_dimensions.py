"""Allow dimension presets from local device profiles in F006."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_profile_dimensions"
down_revision = "0008_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("processed_page") as batch:
        batch.drop_constraint("ck_processed_page_profile_size", type_="check")
        batch.create_check_constraint(
            "ck_processed_page_profile_size",
            "width BETWEEN 1 AND 10000 AND height BETWEEN 1 AND 10000 "
            "AND width * height <= 50000000",
        )


def downgrade() -> None:
    processed_page = sa.table(
        "processed_page",
        sa.column("width", sa.Integer()),
        sa.column("height", sa.Integer()),
    )
    incompatible_count = op.get_bind().scalar(
        sa.select(sa.func.count())
        .select_from(processed_page)
        .where(sa.or_(processed_page.c.width != 600, processed_page.c.height != 800))
    )
    if incompatible_count:
        raise RuntimeError(
            "Não é possível reverter F011: há páginas processadas fora de 600 × 800."
        )
    with op.batch_alter_table("processed_page") as batch:
        batch.drop_constraint("ck_processed_page_profile_size", type_="check")
        batch.create_check_constraint(
            "ck_processed_page_profile_size",
            "width = 600 AND height = 800",
        )
