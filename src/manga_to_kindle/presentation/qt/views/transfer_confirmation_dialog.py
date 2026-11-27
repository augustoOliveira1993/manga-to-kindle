"""Confirmação explícita de metadados e destinatário para uma tentativa SMTP."""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.transfers.smtp_send import TransferConsent, TransferPreview


class TransferConfirmationDialog(QDialog):
    def __init__(self, preview: TransferPreview, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preview = preview
        self.setWindowTitle("Confirmar envio por e-mail")
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "O EPUB e os dados abaixo sairão deste dispositivo e serão enviados ao servidor "
            "SMTP configurado. Revise cada valor; esta confirmação vale somente "
            "para esta tentativa."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        artifact = preview.artifact
        profile = preview.profile
        details = QLabel(
            f"Arquivo: {artifact.path.name}\n"
            f"Pasta: {artifact.path.parent}\n"
            f"Tamanho: {artifact.size_bytes:,} bytes\n"
            f"SHA-256: {artifact.sha256[:12]}…\n"
            f"Destino Kindle: {profile.recipient}\n"
            f"Remetente: {profile.sender}\n"
            f"Servidor: {profile.host}:{profile.port} ({profile.tls_mode.value.upper()})\n"
            f"Assunto: {preview.subject}\n"
            f"Corpo: {preview.body}\n"
            f"Tamanho estimado da mensagem: {preview.estimated_message_bytes:,} bytes"
        )
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details.setWordWrap(True)
        details.setAccessibleName("Detalhes do arquivo e do destino SMTP")
        layout.addWidget(details)

        if preview.possible_duplicate:
            duplicate = QLabel(
                "Este EPUB já foi aceito por um servidor SMTP anteriormente. Um novo envio "
                "pode criar uma cópia duplicada no Kindle."
            )
            duplicate.setWordWrap(True)
            layout.addWidget(duplicate)
        else:
            duplicate = None

        self.recipient_check = QCheckBox(
            "Confirmo que este é o meu endereço Kindle correto e autorizado."
        )
        self.sender_check = QCheckBox(
            "Confirmo que o remetente está na lista autorizada da minha conta Amazon "
            "(autodeclaração, não verificada pelo aplicativo)."
        )
        self.duplicate_check = QCheckBox("Aceito o risco de criar uma cópia duplicada.")
        for checkbox in (self.recipient_check, self.sender_check):
            checkbox.setChecked(False)
            layout.addWidget(checkbox)
        if duplicate is not None:
            self.duplicate_check.setChecked(False)
            layout.addWidget(self.duplicate_check)
        else:
            self.duplicate_check.setChecked(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            parent=self,
        )
        self.send_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.send_button.setText("Enviar esta tentativa")
        self.send_button.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.recipient_check.toggled.connect(self._update_send_enabled)
        self.sender_check.toggled.connect(self._update_send_enabled)
        self.duplicate_check.toggled.connect(self._update_send_enabled)

    def consent(self) -> TransferConsent:
        return TransferConsent(
            preview=self._preview,
            recipient_confirmed=self.recipient_check.isChecked(),
            sender_authorized=self.sender_check.isChecked(),
            duplicate_acknowledged=self.duplicate_check.isChecked(),
            consented_at=datetime.now(UTC),
        )

    def _update_send_enabled(self) -> None:
        self.send_button.setEnabled(
            self.recipient_check.isChecked()
            and self.sender_check.isChecked()
            and self.duplicate_check.isChecked()
        )
