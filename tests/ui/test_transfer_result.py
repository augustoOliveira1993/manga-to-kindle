from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from manga_to_kindle.application.transfers.smtp_send import TransferPreview
from manga_to_kindle.domain.transfers import (
    ExportTransferArtifact,
    SmtpProfile,
    TlsMode,
    TransferHistoryItem,
    TransferJob,
    TransferState,
)
from manga_to_kindle.presentation.qt.views.transfer_confirmation_dialog import (
    TransferConfirmationDialog,
)
from manga_to_kindle.presentation.qt.views.transfer_history_view import _history_label


def _preview(*, duplicate: bool = False) -> TransferPreview:
    artifact = ExportTransferArtifact(
        id=uuid4(),
        export_id=uuid4(),
        package_id=uuid4(),
        format="epub",
        path=Path("C:/test/chapter.epub"),
        sha256="a" * 64,
        size_bytes=1024,
    )
    profile = SmtpProfile(
        host="smtp.example.test",
        port=587,
        tls_mode=TlsMode.STARTTLS,
        sender="reader@example.test",
        recipient="private-device@kindle.com",
        username=None,
        credential_ref=None,
        sender_authorized=True,
        recipient_confirmed=True,
    )
    return TransferPreview(
        artifact,
        profile,
        "chapter",
        "Documento EPUB enviado pelo Manga to Kindle.",
        4096,
        duplicate,
    )


def test_confirmation_dialog_requires_explicit_recipient_and_sender_checks(qt_core_app) -> None:
    dialog = TransferConfirmationDialog(_preview())
    assert not dialog.send_button.isEnabled()
    dialog.recipient_check.setChecked(True)
    assert not dialog.send_button.isEnabled()
    dialog.sender_check.setChecked(True)
    assert dialog.send_button.isEnabled()

    QTest.mouseClick(dialog.send_button, Qt.MouseButton.LeftButton)

    assert dialog.result() == dialog.DialogCode.Accepted
    consent = dialog.consent()
    assert consent.recipient_confirmed
    assert consent.sender_authorized
    assert consent.consented_at.tzinfo is UTC


def test_duplicate_warning_requires_its_own_acknowledgement(qt_core_app) -> None:
    dialog = TransferConfirmationDialog(_preview(duplicate=True))
    dialog.recipient_check.setChecked(True)
    dialog.sender_check.setChecked(True)
    assert not dialog.send_button.isEnabled()
    dialog.duplicate_check.setChecked(True)
    assert dialog.send_button.isEnabled()


def test_history_never_labels_smtp_acceptance_as_kindle_delivery() -> None:
    now = datetime.now(UTC)
    job = TransferJob(
        id=uuid4(),
        artifact_id=uuid4(),
        export_id=uuid4(),
        artifact_sha256="a" * 64,
        artifact_size_bytes=1024,
        state=TransferState.ACCEPTED_BY_SMTP,
        stage="finished",
        host="smtp.example.test",
        port=587,
        tls_mode=TlsMode.STARTTLS,
        sender="reader@example.test",
        masked_recipient="p***@kindle.com",
        consented_at=now,
        created_at=now,
        updated_at=now,
    )

    label = _history_label(TransferHistoryItem(job, "chapter.epub"))

    assert "Aceito pelo servidor SMTP" in label
    assert "entrega ao Kindle não confirmada" in label
    assert "Entregue" not in label
    assert "private-device@kindle.com" not in label
