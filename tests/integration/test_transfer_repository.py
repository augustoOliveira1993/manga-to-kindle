from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.domain.transfers import ExportTransferArtifact, SmtpProfile, TlsMode, TransferState
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    ExportArtifactRecord,
    ExportRecord,
)
from manga_to_kindle.infrastructure.persistence.transfer_repository import TransferRepository


def _profile() -> SmtpProfile:
    return SmtpProfile(
        host="smtp.example.test",
        port=587,
        tls_mode=TlsMode.STARTTLS,
        sender="reader@example.test",
        recipient="device@kindle.com",
        username="reader@example.test",
        credential_ref=str(uuid4()),
        sender_authorized=True,
        recipient_confirmed=True,
    )


def _artifact(path: Path) -> ExportTransferArtifact:
    return ExportTransferArtifact(
        id=uuid4(),
        export_id=uuid4(),
        package_id=uuid4(),
        format="epub",
        path=path,
        sha256="a" * 64,
        size_bytes=100,
    )


def _seed_artifact(database: SQLiteDatabase, artifact: ExportTransferArtifact) -> None:
    now = datetime.now(UTC)
    with database.unit_of_work() as session:
        session.add(
            ExportRecord(
                id=artifact.export_id,
                profile_snapshot={"items": []},
                destination=str(artifact.path.parent),
                state="completed",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ExportArtifactRecord(
                id=artifact.id,
                export_id=artifact.export_id,
                package_id=artifact.package_id,
                position=0,
                format=artifact.format,
                path=str(artifact.path),
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
                chapter_ids=[str(uuid4())],
                created_at=now,
            )
        )


def test_transfer_profile_and_history_persist_only_secret_reference(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "state.sqlite3")
    database.initialize()
    repository = TransferRepository(database)
    profile = _profile()
    artifact = _artifact(tmp_path / "private-title.epub")
    _seed_artifact(database, artifact)

    assert repository.save_profile(profile) is None
    assert repository.get_profile() == profile
    job_id = repository.create_attempt(artifact, profile, consented_at=datetime.now(UTC))
    repository.update_attempt(
        job_id,
        TransferState.ACCEPTED_BY_SMTP,
        "finished",
        smtp_code=250,
    )

    history = repository.list_history()
    assert len(history) == 1
    assert history[0].filename == "private-title.epub"
    assert history[0].job.state is TransferState.ACCEPTED_BY_SMTP
    assert history[0].job.masked_recipient == "d***@kindle.com"
    with database.engine.connect() as connection:
        profile_text = connection.exec_driver_sql("SELECT * FROM smtp_profile").all()
        job_text = connection.exec_driver_sql("SELECT * FROM transfer_job").all()
    serialized = repr((profile_text, job_text))
    assert profile.credential_ref in serialized
    assert "super-secret" not in serialized
    assert "device@kindle.com" not in repr(job_text)
    assert "device@kindle.com" in repr(profile_text)
    database.close()


def test_startup_reconciliation_marks_post_data_attempt_unknown_and_never_retries(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "state.sqlite3")
    database.initialize()
    repository = TransferRepository(database)
    profile = _profile()
    artifact = _artifact(tmp_path / "chapter.epub")
    _seed_artifact(database, artifact)
    job_id = repository.create_attempt(artifact, profile, consented_at=datetime.now(UTC))
    repository.update_attempt(job_id, TransferState.TRANSMITTING, "transmitting")

    assert repository.reconcile_interrupted() == 1
    history = repository.list_history()
    assert history[0].job.state is TransferState.UNKNOWN
    assert history[0].job.error_code == "APP_INTERRUPTED"
    assert repository.reconcile_interrupted() == 0
    database.close()
