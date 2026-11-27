from __future__ import annotations

import hashlib
import ssl
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from uuid import uuid4

import manga_to_kindle.infrastructure.transfers.smtp_transport as smtp_module
from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.transfers.smtp_send import (
    PreviewSmtpTransfer,
    SendSmtpTransfer,
    TransferConsent,
)
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import ExportFormat, ExportGrouping, ExportRequest
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.transfers import SmtpProfile, TlsMode, TransferState
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.transfer_repository import TransferRepository
from manga_to_kindle.infrastructure.transfers.smtp_transport import SmtpTransport
from manga_to_kindle.presentation.qt.workers.adapter import CancellationToken
from tests.image_support import FIXTURES as IMAGE_FIXTURES
from tests.image_support import make_image_stack, make_new_target
from tests.transfers_support import FIXTURES, SCENARIOS, LocalSmtpServer


class FakeVault:
    def __init__(self, password: str = "smtp-local-test-secret") -> None:
        self.password = password
        self.references: list[str] = []

    def get(self, reference: str) -> str:
        self.references.append(reference)
        return self.password


def _export_real_epub(tmp_path: Path) -> tuple[object, ExportRepository, Path]:
    database, _root, _store, _repository, _reader, _decoder, importer = make_image_stack(
        tmp_path / "profile"
    )
    target = make_new_target("SMTP integration", "Capítulo 1")
    plan = importer.preview_source(IMAGE_FIXTURES / "valid")
    importer.execute(plan, target, confirmed_authorization=True)
    output = tmp_path / "exports"
    output.mkdir()
    export_repository = ExportRepository(database)
    workflow = CreateExport(
        export_repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
    )
    result = workflow.execute(
        ExportRequest(
            chapter_ids=(target.chapter_id,),
            output_directory=output.resolve(),
            profile=DeviceProfile("600 × 800", preferences={"width": 600, "height": 800}),
            format=ExportFormat.EPUB,
            grouping=ExportGrouping.CHAPTER,
            direction=ReadingDirection.RIGHT_TO_LEFT,
            language="pt-BR",
        )
    )
    assert ValidateEpub().execute(result.output_paths[0]).page_count > 0
    return database, export_repository, result.output_paths[0]


def _profile(
    server: LocalSmtpServer,
    *,
    authenticated: bool = False,
    tls_mode: TlsMode = TlsMode.STARTTLS,
) -> SmtpProfile:
    return SmtpProfile(
        host="localhost",
        port=server.port,
        tls_mode=tls_mode,
        sender="reader@example.test",
        recipient="device@kindle.com",
        username="reader@example.test" if authenticated else None,
        credential_ref=str(uuid4()) if authenticated else None,
        sender_authorized=True,
        recipient_confirmed=True,
    )


def _trust_local_test_cert(monkeypatch) -> None:
    context = ssl.create_default_context(cafile=str(FIXTURES / "localhost-test-cert.pem"))
    monkeypatch.setattr(smtp_module.ssl, "create_default_context", lambda: context)


def _execute_real_export_send(
    tmp_path: Path,
    server: LocalSmtpServer,
    *,
    monkeypatch,
    authenticated: bool = False,
    vault: FakeVault | None = None,
):
    database, export_repository, epub_path = _export_real_epub(tmp_path)
    transfer_repository = TransferRepository(database)
    profile = _profile(server, authenticated=authenticated)
    transfer_repository.save_profile(profile)
    artifact = export_repository.list_transfer_artifacts()[0]
    preview = PreviewSmtpTransfer(
        export_repository,
        transfer_repository,
        transfer_repository,
    ).execute(artifact.id)
    consent = TransferConsent(
        preview=preview,
        recipient_confirmed=True,
        sender_authorized=True,
        duplicate_acknowledged=False,
        consented_at=datetime.now(UTC),
    )
    vault_adapter = vault or FakeVault()
    service = SendSmtpTransfer(
        export_repository,
        transfer_repository,
        transfer_repository,
        vault_adapter,
        SmtpTransport(),
    )
    progress: list[str] = []
    result = service.execute(
        consent,
        cancellation=CancellationToken(),
        report_progress=lambda _done, _total, message: progress.append(message),
    )
    history = transfer_repository.list_history()
    database.close()
    return result, history, epub_path, progress, vault_adapter


def test_smtp_local_tls_submission_attaches_the_unmodified_f007_epub(
    tmp_path: Path,
    monkeypatch,
    caplog,
) -> None:
    _trust_local_test_cert(monkeypatch)
    secret = "smtp-local-test-secret"
    vault = FakeVault(secret)
    with LocalSmtpServer() as server:
        result, history, epub_path, progress, _vault = _execute_real_export_send(
            tmp_path,
            server,
            monkeypatch=monkeypatch,
            authenticated=True,
            vault=vault,
        )

    assert result.state is TransferState.ACCEPTED_BY_SMTP
    assert result.smtp_code == SCENARIOS["accepted"]
    assert history[0].job.state is TransferState.ACCEPTED_BY_SMTP
    assert history[0].job.masked_recipient == "d***@kindle.com"
    assert server.error is None
    assert "STARTTLS" in " ".join(server.commands)
    assert server.commands.index("STARTTLS") < next(
        index for index, command in enumerate(server.commands) if command.startswith("AUTH ")
    )
    message = BytesParser(policy=policy.default).parsebytes(server.received_message)
    attachment = next(part for part in message.iter_attachments())
    assert attachment.get_filename() == epub_path.name
    assert attachment.get_payload(decode=True) == epub_path.read_bytes()
    assert hashlib.sha256(attachment.get_payload(decode=True)).hexdigest() == hashlib.sha256(
        epub_path.read_bytes()
    ).hexdigest()
    assert "entrega ao Kindle não confirmada" in progress[-1]
    assert secret not in caplog.text
    assert secret not in repr(history)
    assert vault.references


def test_local_smtp_temporary_and_permanent_data_rejections_are_distinguished(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _trust_local_test_cert(monkeypatch)
    observed: list[TransferState] = []
    for code, expected in (
        (SCENARIOS["temporary_rejection"], TransferState.REJECTED_TEMPORARY),
        (SCENARIOS["permanent_rejection"], TransferState.REJECTED_PERMANENT),
    ):
        scenario_directory = tmp_path / str(code)
        scenario_directory.mkdir()
        with LocalSmtpServer(data_code=code) as server:
            result, history, _epub, _progress, _vault = _execute_real_export_send(
                scenario_directory,
                server,
                monkeypatch=monkeypatch,
            )
        assert result.state is expected
        assert history[0].job.smtp_code == code
        assert server.received_message
        observed.append(result.state)
    assert observed == [TransferState.REJECTED_TEMPORARY, TransferState.REJECTED_PERMANENT]


def test_disconnect_after_local_smtp_data_is_unknown_without_automatic_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _trust_local_test_cert(monkeypatch)
    with LocalSmtpServer(
        disconnect_after_data=SCENARIOS["disconnect_after_data"],
    ) as server:
        result, history, _epub, _progress, _vault = _execute_real_export_send(
            tmp_path,
            server,
            monkeypatch=monkeypatch,
        )

    assert result.state is TransferState.UNKNOWN
    assert history[0].job.state is TransferState.UNKNOWN
    assert server.received_message
    assert len(history) == 1


def test_explicit_connection_test_never_submits_a_message(
    monkeypatch,
) -> None:
    _trust_local_test_cert(monkeypatch)
    with LocalSmtpServer() as server:
        SmtpTransport().test_connection(_profile(server), None)

    assert server.error is None
    assert "STARTTLS" in server.commands
    assert not any(
        command.startswith(("MAIL FROM:", "RCPT TO:")) or command == "DATA"
        for command in server.commands
    )


def test_implicit_tls_uses_local_tls_server_without_starttls_downgrade(
    monkeypatch,
) -> None:
    _trust_local_test_cert(monkeypatch)
    with LocalSmtpServer(implicit_tls=True) as server:
        SmtpTransport().test_connection(
            _profile(server, tls_mode=TlsMode.IMPLICIT),
            None,
        )

    assert server.error is None
    assert not any(command == "STARTTLS" for command in server.commands)
    assert server.commands[0].upper().startswith("EHLO ")


def test_untrusted_local_certificate_blocks_smtp_before_message_submission(
    tmp_path: Path,
) -> None:
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"local-only test payload")
    content = path.read_bytes()
    with LocalSmtpServer() as server:
        result = SmtpTransport().send(
            profile=_profile(server),
            password=None,
            file_path=path,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            expected_size=len(content),
            cancellation=CancellationToken(),
            report_stage=lambda *_args: None,
        )

    assert result.state is TransferState.FAILED_BEFORE_SUBMISSION
    assert result.error_code == "SMTP_CONNECTION_FAILED"
    assert "DATA" not in server.commands
    assert server.received_message == b""
