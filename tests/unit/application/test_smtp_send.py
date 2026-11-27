from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.application.transfers.smtp_send import (
    PreviewSmtpTransfer,
    SendSmtpTransfer,
    TransferConsent,
    TransferConsentExpired,
    TransferNotConfirmed,
)
from manga_to_kindle.domain.transfers import (
    ExportTransferArtifact,
    SmtpProfile,
    TlsMode,
    TransferState,
)
from manga_to_kindle.infrastructure.transfers.smtp_transport import SmtpTransportResult


class ArtifactStore:
    def __init__(self, artifact: ExportTransferArtifact) -> None:
        self.artifact = artifact

    def get_artifact(self, artifact_id):
        return self.artifact if artifact_id == self.artifact.id else None


class ProfileStore:
    def __init__(self, profile: SmtpProfile) -> None:
        self.profile = profile

    def get_profile(self) -> SmtpProfile:
        return self.profile


class HistoryStore:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.created: list[tuple[ExportTransferArtifact, SmtpProfile, datetime]] = []
        self.updated: list[tuple[TransferState, str, str | None, int | None]] = []

    def has_accepted_attempt(self, _artifact_id) -> bool:
        return self.duplicate

    def create_attempt(self, artifact, profile, *, consented_at):
        self.created.append((artifact, profile, consented_at))
        return uuid4()

    def update_attempt(self, _id, state, stage, *, error_code=None, smtp_code=None):
        self.updated.append((state, stage, error_code, smtp_code))


class FakeVault:
    def __init__(self, password: str = "vault-secret") -> None:
        self.password = password
        self.references: list[str] = []

    def get(self, reference: str) -> str:
        self.references.append(reference)
        return self.password


class FakeTransport:
    def __init__(self, result: SmtpTransportResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["report_stage"]("transmitting", "transmitting")
        return self.result


class NotCancelled:
    cancelled = False


def _services(tmp_path: Path, *, duplicate: bool = False):
    path = tmp_path / "chapter.epub"
    content = b"verified epub test bytes"
    path.write_bytes(content)
    artifact = ExportTransferArtifact(
        id=uuid4(),
        export_id=uuid4(),
        package_id=uuid4(),
        format="epub",
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )
    profile = SmtpProfile(
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
    artifacts = ArtifactStore(artifact)
    profiles = ProfileStore(profile)
    history = HistoryStore(duplicate=duplicate)
    preview = PreviewSmtpTransfer(artifacts, profiles, history).execute(artifact.id)
    transport = FakeTransport(SmtpTransportResult(TransferState.ACCEPTED_BY_SMTP, 250))
    service = SendSmtpTransfer(artifacts, profiles, history, FakeVault(), transport)
    return artifact, profiles, history, preview, transport, service


def _consent(preview, *, destination: bool = True, sender: bool = True, duplicate: bool = False):
    return TransferConsent(
        preview=preview,
        recipient_confirmed=destination,
        sender_authorized=sender,
        duplicate_acknowledged=duplicate,
        consented_at=datetime.now(UTC),
    )


def test_send_requires_both_confirmations_before_creating_attempt_or_network_call(
    tmp_path: Path,
) -> None:
    _artifact, _profiles, history, preview, transport, service = _services(tmp_path)

    with pytest.raises(TransferNotConfirmed):
        service.execute(
            _consent(preview, destination=False),
            cancellation=NotCancelled(),
            report_progress=lambda *_args: None,
        )

    assert history.created == []
    assert transport.calls == []


def test_accepted_server_result_is_recorded_without_claiming_device_delivery(
    tmp_path: Path,
) -> None:
    _artifact, _profiles, history, preview, transport, service = _services(tmp_path)
    progress: list[str] = []

    result = service.execute(
        _consent(preview),
        cancellation=NotCancelled(),
        report_progress=lambda _done, _total, message: progress.append(message),
    )

    assert result.state is TransferState.ACCEPTED_BY_SMTP
    assert result.smtp_code == 250
    assert transport.calls[0]["password"] == "vault-secret"
    assert history.updated[-1][0] is TransferState.ACCEPTED_BY_SMTP
    assert "Aceito pelo servidor SMTP" in progress[-1]
    assert "entrega ao Kindle não confirmada" in progress[-1]


def test_profile_change_after_confirmation_blocks_the_network(tmp_path: Path) -> None:
    _artifact, profiles, history, preview, transport, service = _services(tmp_path)
    profiles.profile = replace(profiles.profile, host="changed.example.test")

    with pytest.raises(TransferConsentExpired):
        service.execute(
            _consent(preview),
            cancellation=NotCancelled(),
            report_progress=lambda *_args: None,
        )

    assert history.created == []
    assert transport.calls == []


def test_accepted_export_requires_explicit_duplicate_acknowledgement(tmp_path: Path) -> None:
    _artifact, _profiles, history, preview, transport, service = _services(
        tmp_path,
        duplicate=True,
    )
    assert preview.possible_duplicate is True

    with pytest.raises(TransferNotConfirmed):
        service.execute(
            _consent(preview),
            cancellation=NotCancelled(),
            report_progress=lambda *_args: None,
        )

    assert history.created == []
    assert transport.calls == []


def test_cancellation_before_submission_is_recorded_without_connecting(tmp_path: Path) -> None:
    class Cancelled:
        cancelled = True

    _artifact, _profiles, history, preview, transport, service = _services(tmp_path)
    result = service.execute(
        _consent(preview),
        cancellation=Cancelled(),
        report_progress=lambda *_args: None,
    )

    assert result.state is TransferState.CANCELLED_BEFORE_SUBMISSION
    assert history.updated[-1][0] is TransferState.CANCELLED_BEFORE_SUBMISSION
    assert transport.calls == []
