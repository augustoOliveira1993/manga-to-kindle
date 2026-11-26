"""Persistência de perfis sem segredo e histórico sanitizado de SMTP."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from manga_to_kindle.domain.transfers import (
    ExportTransferArtifact,
    SmtpProfile,
    TlsMode,
    TransferHistoryItem,
    TransferJob,
    TransferState,
    mask_email,
)
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    ExportArtifactRecord,
    SmtpProfileRecord,
    TransferJobRecord,
)


class TransferPersistenceError(RuntimeError):
    code = "TRANSFER_PERSISTENCE_FAILED"


class TransferRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def get_profile(self) -> SmtpProfile | None:
        with self._database.unit_of_work() as session:
            record = session.get(SmtpProfileRecord, 1)
            return _profile_from_record(record) if record is not None else None

    def save_profile(self, profile: SmtpProfile) -> str | None:
        with self._database.unit_of_work() as session:
            record = session.get(SmtpProfileRecord, 1)
            previous_ref = record.credential_ref if record is not None else None
            if record is None:
                record = SmtpProfileRecord(id=1)
                session.add(record)
            record.host = profile.host
            record.port = profile.port
            record.tls_mode = profile.tls_mode.value
            record.sender = profile.sender
            record.recipient = profile.recipient
            record.username = profile.username
            record.credential_ref = profile.credential_ref
            record.sender_authorized = profile.sender_authorized
            record.recipient_confirmed = profile.recipient_confirmed
            record.updated_at = datetime.now(UTC)
            return previous_ref

    def remove_profile(self) -> str | None:
        with self._database.unit_of_work() as session:
            record = session.get(SmtpProfileRecord, 1)
            if record is None:
                return None
            credential_ref = record.credential_ref
            session.delete(record)
            return credential_ref

    def create_attempt(
        self,
        artifact: ExportTransferArtifact,
        profile: SmtpProfile,
        *,
        consented_at: datetime,
    ) -> UUID:
        now = datetime.now(UTC)
        transfer_id = uuid4()
        with self._database.unit_of_work() as session:
            session.add(
                TransferJobRecord(
                    id=transfer_id,
                    artifact_id=artifact.id,
                    export_id=artifact.export_id,
                    export_sha256=artifact.sha256,
                    size_bytes=artifact.size_bytes,
                    format=artifact.format,
                    state=TransferState.CONNECTING.value,
                    stage="connecting",
                    host=profile.host,
                    port=profile.port,
                    tls_mode=profile.tls_mode.value,
                    sender=profile.sender,
                    recipient_masked=mask_email(profile.recipient),
                    consented_at=consented_at,
                    created_at=now,
                    updated_at=now,
                )
            )
        return transfer_id

    def update_attempt(
        self,
        transfer_id: UUID,
        state: TransferState,
        stage: str,
        *,
        error_code: str | None = None,
        smtp_code: int | None = None,
    ) -> None:
        allowed_stages = {
            "connecting",
            "tls",
            "authenticating",
            "envelope",
            "transmitting",
            "finished",
        }
        if stage not in allowed_stages:
            raise TransferPersistenceError("A etapa de transferência não é permitida.")
        if error_code is not None and not error_code.replace("_", "").isalnum():
            raise TransferPersistenceError("O código de resultado não pode ser persistido.")
        with self._database.unit_of_work() as session:
            record = session.get(TransferJobRecord, transfer_id)
            if record is None:
                raise TransferPersistenceError("A tentativa de transferência não existe.")
            record.state = state.value
            record.stage = stage
            record.error_code = error_code
            record.smtp_code = smtp_code
            record.updated_at = datetime.now(UTC)

    def list_history(self, *, limit: int = 100) -> tuple[TransferHistoryItem, ...]:
        if not 1 <= limit <= 1000:
            raise TransferPersistenceError("O limite do histórico precisa ficar entre 1 e 1000.")
        with self._database.unit_of_work() as session:
            rows = session.execute(
                select(TransferJobRecord, ExportArtifactRecord)
                .join(
                    ExportArtifactRecord,
                    ExportArtifactRecord.id == TransferJobRecord.artifact_id,
                )
                .order_by(TransferJobRecord.created_at.desc())
                .limit(limit)
            ).all()
            return tuple(
                TransferHistoryItem(_job_from_record(job), _safe_filename(artifact.path))
                for job, artifact in rows
            )

    def has_accepted_attempt(self, artifact_id: UUID) -> bool:
        with self._database.unit_of_work() as session:
            transfer_id = session.execute(
                select(TransferJobRecord.id)
                .where(
                    TransferJobRecord.artifact_id == artifact_id,
                    TransferJobRecord.state == TransferState.ACCEPTED_BY_SMTP.value,
                )
                .limit(1)
            ).scalar_one_or_none()
            return transfer_id is not None

    def reconcile_interrupted(self) -> int:
        active_states = {
            TransferState.CONNECTING.value,
            TransferState.AUTHENTICATING.value,
            TransferState.TRANSMITTING.value,
        }
        changed = 0
        with self._database.unit_of_work() as session:
            records = tuple(
                session.scalars(
                    select(TransferJobRecord).where(TransferJobRecord.state.in_(active_states))
                )
            )
            now = datetime.now(UTC)
            for record in records:
                record.state = (
                    TransferState.UNKNOWN.value
                    if record.stage == "transmitting"
                    else TransferState.INTERRUPTED.value
                )
                record.stage = "finished"
                record.error_code = "APP_INTERRUPTED"
                record.updated_at = now
                changed += 1
        return changed


def _profile_from_record(record: SmtpProfileRecord) -> SmtpProfile:
    return SmtpProfile(
        host=record.host,
        port=record.port,
        tls_mode=TlsMode(record.tls_mode),
        sender=record.sender,
        recipient=record.recipient,
        username=record.username,
        credential_ref=record.credential_ref,
        sender_authorized=record.sender_authorized,
        recipient_confirmed=record.recipient_confirmed,
    )


def _job_from_record(record: TransferJobRecord) -> TransferJob:
    return TransferJob(
        id=record.id,
        artifact_id=record.artifact_id,
        export_id=record.export_id,
        artifact_sha256=record.export_sha256,
        artifact_size_bytes=record.size_bytes,
        state=TransferState(record.state),
        stage=record.stage,
        host=record.host,
        port=record.port,
        tls_mode=TlsMode(record.tls_mode),
        sender=record.sender,
        masked_recipient=record.recipient_masked,
        consented_at=record.consented_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_code=record.error_code,
        smtp_code=record.smtp_code,
    )


def _safe_filename(path: str) -> str:
    from pathlib import PurePath

    return PurePath(path).name
