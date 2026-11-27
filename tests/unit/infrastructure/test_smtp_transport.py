from __future__ import annotations

import hashlib
import ssl
from pathlib import Path
from uuid import uuid4

import manga_to_kindle.infrastructure.transfers.smtp_transport as smtp_module
from manga_to_kindle.application.transfers.ports import estimate_message_size
from manga_to_kindle.domain.transfers import SmtpProfile, TlsMode, TransferState
from manga_to_kindle.presentation.qt.workers.adapter import CancellationToken


class FakeSmtpClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.has_starttls = True
        self.starttls_error: Exception | None = None
        self.mail_code = 250
        self.recipient_code = 250
        self.data_code = 250
        self.disconnect_during_data = False
        self.message: bytes | None = None
        self.login_values: tuple[str, str] | None = None
        self.quit_called = False
        self.close_called = False
        self.context = None
        self.esmtp_features: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def ehlo(self):
        self.esmtp_features = {"starttls": "", "size": "50000000"}
        return 250, b"hello"

    def ehlo_or_helo_if_needed(self):
        return self.ehlo()

    def has_extn(self, name: str) -> bool:
        return name == "starttls" and self.has_starttls

    def starttls(self, *, context):
        self.context = context
        if not self.has_starttls:
            raise smtp_module.smtplib.SMTPNotSupportedError("STARTTLS unavailable")
        if self.starttls_error is not None:
            raise self.starttls_error
        return 220, b"ready"

    def login(self, username: str, password: str) -> None:
        self.login_values = username, password

    def mail(self, sender: str, options=()):
        self.mail_options = options
        return self.mail_code, b"sender"

    def rcpt(self, recipient: str):
        return self.recipient_code, b"recipient"

    def data(self, message: bytes):
        self.message = message
        if self.disconnect_during_data:
            raise smtp_module.smtplib.SMTPServerDisconnected("secret response not logged")
        return self.data_code, b"response"

    def quit(self):
        self.quit_called = True
        return 221, b"bye"

    def close(self) -> None:
        self.close_called = True


def _profile(mode: TlsMode = TlsMode.STARTTLS) -> SmtpProfile:
    return SmtpProfile(
        host="smtp.example.test",
        port=465 if mode is TlsMode.IMPLICIT else 587,
        tls_mode=mode,
        sender="reader@example.test",
        recipient="device@kindle.com",
        username="reader@example.test",
        credential_ref=str(uuid4()),
        sender_authorized=True,
        recipient_confirmed=True,
    )


def _run_send(path: Path, client: FakeSmtpClient, monkeypatch, profile: SmtpProfile | None = None):
    def factory(*_args: object, **kwargs: object) -> FakeSmtpClient:
        client.kwargs = kwargs
        return client

    monkeypatch.setattr(smtp_module.smtplib, "SMTP", factory)
    monkeypatch.setattr(smtp_module.smtplib, "SMTP_SSL", factory)
    data = path.read_bytes()
    progress: list[tuple[str, str]] = []
    result = smtp_module.SmtpTransport().send(
        profile=profile or _profile(),
        password="vault-sentinel",
        file_path=path,
        expected_sha256=hashlib.sha256(data).hexdigest(),
        expected_size=len(data),
        cancellation=CancellationToken(),
        report_stage=lambda stage, message: progress.append((stage, message)),
    )
    return result, progress


def test_transport_requires_validated_starttls_before_authentication_or_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    client = FakeSmtpClient()

    result, progress = _run_send(path, client, monkeypatch)

    assert result.state is TransferState.ACCEPTED_BY_SMTP
    assert client.context.check_hostname is True
    assert client.context.verify_mode == ssl.CERT_REQUIRED
    assert client.login_values == ("reader@example.test", "vault-sentinel")
    assert client.message is not None
    assert b"To: device@kindle.com" in client.message
    assert b"chapter.epub" in client.message
    assert [stage for stage, _message in progress] == [
        "tls",
        "authenticating",
        "envelope",
        "transmitting",
    ]


def test_transport_fails_closed_when_starttls_is_not_available(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    client = FakeSmtpClient()
    client.has_starttls = False

    result, _progress = _run_send(path, client, monkeypatch)

    assert result.state is TransferState.FAILED_BEFORE_SUBMISSION
    assert result.error_code == "SMTP_CONNECTION_FAILED"
    assert client.login_values is None
    assert client.message is None


def test_connection_timeout_fails_before_sending_message(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    client = FakeSmtpClient()

    def timeout(*_args: object, **_kwargs: object) -> FakeSmtpClient:
        raise TimeoutError("connection timed out")

    monkeypatch.setattr(smtp_module.smtplib, "SMTP", timeout)
    monkeypatch.setattr(smtp_module.smtplib, "SMTP_SSL", timeout)
    content = path.read_bytes()
    result = smtp_module.SmtpTransport().send(
        profile=_profile(),
        password="vault-sentinel",
        file_path=path,
        expected_sha256=hashlib.sha256(content).hexdigest(),
        expected_size=len(content),
        cancellation=CancellationToken(),
        report_stage=lambda *_args: None,
    )

    assert result.state is TransferState.FAILED_BEFORE_SUBMISSION
    assert result.error_code == "SMTP_CONNECTION_FAILED"
    assert client.message is None


def test_transport_classifies_explicit_4xx_and_5xx_rejections(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    temporary = FakeSmtpClient()
    temporary.data_code = 451
    permanent = FakeSmtpClient()
    permanent.data_code = 550
    results = []
    for client in (temporary, permanent):
        result, _progress = _run_send(path, client, monkeypatch)
        results.append(result)

    assert results[0].state is TransferState.REJECTED_TEMPORARY
    assert results[0].smtp_code == 451
    assert results[1].state is TransferState.REJECTED_PERMANENT
    assert results[1].smtp_code == 550


def test_disconnect_during_data_is_unknown_and_never_claimed_as_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    client = FakeSmtpClient()
    client.disconnect_during_data = True

    result, _progress = _run_send(path, client, monkeypatch)

    assert result.state is TransferState.UNKNOWN
    assert result.error_code == "SMTP_RESULT_UNKNOWN"
    assert "secret response" not in repr(result)


def test_transport_rejects_changed_artifact_before_connecting(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"original")
    expected_sha256 = hashlib.sha256(b"original").hexdigest()
    client = FakeSmtpClient()
    connections: list[bool] = []
    def factory(*_args: object, **_kwargs: object) -> FakeSmtpClient:
        connections.append(True)
        return client

    monkeypatch.setattr(smtp_module.smtplib, "SMTP", factory)
    monkeypatch.setattr(smtp_module.smtplib, "SMTP_SSL", factory)
    path.write_bytes(b"changed")
    result = smtp_module.SmtpTransport().send(
        profile=_profile(),
        password="vault-sentinel",
        file_path=path,
        expected_sha256=expected_sha256,
        expected_size=len(b"original"),
        cancellation=CancellationToken(),
        report_stage=lambda *_args: None,
    )
    assert result.state is TransferState.FAILED_BEFORE_SUBMISSION
    assert result.error_code == "ARTIFACT_CHANGED"
    assert connections == []


def test_transport_supports_implicit_tls_with_default_certificate_validation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"epub bytes")
    client = FakeSmtpClient()

    result, _progress = _run_send(
        path,
        client,
        monkeypatch,
        profile=_profile(TlsMode.IMPLICIT),
    )

    assert result.state is TransferState.ACCEPTED_BY_SMTP
    context = client.kwargs["context"]
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert client.message is not None


def test_estimated_email_size_includes_base64_and_mime_overhead() -> None:
    size = estimate_message_size(1_000_000, "manga.epub")
    assert size > 1_333_333
    assert size < 1_400_000
