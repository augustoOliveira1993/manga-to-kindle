"""Perfis SMTP sem segredo e histórico de tentativas autorizadas F009."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_transfers"
down_revision = "0006_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smtp_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(length=253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("tls_mode", sa.String(length=16), nullable=False),
        sa.Column("sender", sa.String(length=254), nullable=False),
        sa.Column("recipient", sa.String(length=254), nullable=False),
        sa.Column("username", sa.String(length=513), nullable=True),
        sa.Column("credential_ref", sa.String(length=36), nullable=True),
        sa.Column("sender_authorized", sa.Boolean(), nullable=False),
        sa.Column("recipient_confirmed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_smtp_profile_singleton"),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="ck_smtp_profile_port"),
        sa.CheckConstraint("tls_mode IN ('starttls', 'implicit')", name="ck_smtp_profile_tls"),
        sa.CheckConstraint(
            "(username IS NULL AND credential_ref IS NULL) OR "
            "(username IS NOT NULL AND credential_ref IS NOT NULL)",
            name="ck_smtp_profile_auth_reference",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transfer_job",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("artifact_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("export_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("export_sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("host", sa.String(length=253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("tls_mode", sa.String(length=16), nullable=False),
        sa.Column("sender", sa.String(length=254), nullable=False),
        sa.Column("recipient_masked", sa.String(length=254), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("smtp_code", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "state IN ('connecting', 'authenticating', 'transmitting', "
            "'accepted_by_smtp', 'rejected_temporary', 'rejected_permanent', "
            "'failed_before_submission', 'cancelled_before_submission', 'unknown', 'interrupted')",
            name="ck_transfer_job_state",
        ),
        sa.CheckConstraint(
            "stage IN ('connecting', 'tls', 'authenticating', 'envelope', "
            "'transmitting', 'finished')",
            name="ck_transfer_job_stage",
        ),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="ck_transfer_job_port"),
        sa.CheckConstraint("length(export_sha256) = 64", name="ck_transfer_job_sha256"),
        sa.CheckConstraint("size_bytes > 0", name="ck_transfer_job_size"),
        sa.CheckConstraint("tls_mode IN ('starttls', 'implicit')", name="ck_transfer_job_tls"),
        sa.ForeignKeyConstraint(["artifact_id"], ["export_artifact.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_job_created", "transfer_job", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_transfer_job_created", table_name="transfer_job")
    op.drop_table("transfer_job")
    op.drop_table("smtp_profile")
