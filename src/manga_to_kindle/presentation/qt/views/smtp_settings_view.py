"""Configuração opt-in de SMTP, com senha somente no cofre do Windows."""

from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.transfers.smtp_settings import (
    ProfileSaveResult,
    RemoveSmtpProfile,
    SaveSmtpProfile,
    TestSmtpConnection,
)
from manga_to_kindle.domain.transfers import SmtpProfile, TlsMode
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)


class SmtpProfileReader(Protocol):
    def get_profile(self) -> SmtpProfile | None: ...


class SmtpSettingsView(QWidget):
    profile_available_changed = Signal(bool)

    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: SmtpProfileReader | None = None
        self._save_service: SaveSmtpProfile | None = None
        self._remove_service: RemoveSmtpProfile | None = None
        self._test_service: TestSmtpConnection | None = None
        self._operations: dict[str, str] = {}
        self._profile_loaded = False
        self._has_profile = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        self.group = QGroupBox("Envio opcional por e-mail (SMTP)")
        self.group.setObjectName("smtpSettingsGroup")
        layout = QVBoxLayout(self.group)
        intro = QLabel(
            "O remetente e o endereço Kindle não são verificados na Amazon. A senha, quando "
            "usada, fica exclusivamente no Gerenciador de Credenciais do Windows."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.host_input = QLineEdit()
        self.host_input.setObjectName("smtpHost")
        self.host_input.setPlaceholderText("smtp.exemplo.com")
        self.host_input.setAccessibleName("Servidor SMTP")
        form.addRow("Servidor SMTP", self.host_input)
        self.port_input = QSpinBox()
        self.port_input.setObjectName("smtpPort")
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(587)
        form.addRow("Porta", self.port_input)
        self.tls_combo = QComboBox()
        self.tls_combo.setObjectName("smtpTlsMode")
        self.tls_combo.addItem("STARTTLS obrigatório", TlsMode.STARTTLS.value)
        self.tls_combo.addItem("TLS implícito", TlsMode.IMPLICIT.value)
        form.addRow("Proteção", self.tls_combo)
        self.sender_input = QLineEdit()
        self.sender_input.setObjectName("smtpSender")
        self.sender_input.setPlaceholderText("voce@exemplo.com")
        form.addRow("Remetente", self.sender_input)
        self.recipient_input = QLineEdit()
        self.recipient_input.setObjectName("smtpRecipient")
        self.recipient_input.setPlaceholderText("seu-endereco@kindle.com")
        form.addRow("Endereço Kindle", self.recipient_input)
        self.username_input = QLineEdit()
        self.username_input.setObjectName("smtpUsername")
        self.username_input.setAccessibleName("Usuário SMTP opcional")
        form.addRow("Usuário (se exigido)", self.username_input)
        self.password_input = QLineEdit()
        self.password_input.setObjectName("smtpPassword")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setAccessibleName("Senha SMTP; não é salva em arquivo")
        self.password_input.setPlaceholderText("Deixe vazio para manter a senha guardada")
        form.addRow("Senha (cofre Windows)", self.password_input)
        layout.addLayout(form)

        self.recipient_check = QCheckBox(
            "Confirmo que o endereço de destino é meu endereço Kindle correto."
        )
        self.recipient_check.setObjectName("smtpRecipientConfirmed")
        self.sender_check = QCheckBox(
            "Confirmo que o remetente está na lista de endereços autorizados da Amazon "
            "(autodeclaração não verificada)."
        )
        self.sender_check.setObjectName("smtpSenderAuthorized")
        layout.addWidget(self.recipient_check)
        layout.addWidget(self.sender_check)

        controls = QHBoxLayout()
        self.save_button = QPushButton("Salvar perfil SMTP")
        self.save_button.setObjectName("saveSmtpProfile")
        self.test_button = QPushButton("Testar conexão")
        self.test_button.setObjectName("testSmtpConnection")
        self.remove_button = QPushButton("Remover perfil e credencial")
        self.remove_button.setObjectName("removeSmtpProfile")
        self.remove_button.setEnabled(False)
        controls.addWidget(self.save_button)
        controls.addWidget(self.test_button)
        controls.addWidget(self.remove_button)
        layout.addLayout(controls)

        self.status_label = QLabel("SMTP não configurado; o fluxo manual permanece disponível.")
        self.status_label.setObjectName("smtpSettingsStatus")
        self.status_label.setAccessibleName("Estado das configurações SMTP")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        outer.addWidget(self.group)

        self.save_button.clicked.connect(self.save_profile)
        self.test_button.clicked.connect(self.test_connection)
        self.remove_button.clicked.connect(self.remove_profile)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.failed.connect(self._on_failed)
        self._runner.cancelled.connect(self._on_cancelled)
        self._runner.finished.connect(self._on_finished)
        self.recipient_check.toggled.connect(self._update_save_enabled)
        self.sender_check.toggled.connect(self._update_save_enabled)
        self.recipient_input.textEdited.connect(self._clear_recipient_confirmation)
        self.sender_input.textEdited.connect(self._clear_sender_confirmation)
        self._set_busy(False)

    def bind_services(
        self,
        repository: SmtpProfileReader,
        save_service: SaveSmtpProfile,
        remove_service: RemoveSmtpProfile,
        test_service: TestSmtpConnection,
        *,
        vault_available: bool = True,
    ) -> None:
        self._repository = repository
        self._save_service = save_service
        self._remove_service = remove_service
        self._test_service = test_service
        if not vault_available:
            self.disable_secure_vault()
            return
        self.refresh_profile()

    def disable_secure_vault(self) -> None:
        self.group.setEnabled(False)
        self.profile_available_changed.emit(False)
        self.status_label.setText(
            "O cofre seguro do Windows não está disponível. SMTP está desativado; "
            "nenhuma senha será gravada em arquivo."
        )

    def refresh_profile(self) -> None:
        if self._repository is None or self._profile_loaded:
            return
        repository = self._repository

        def load(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> SmtpProfile | None:
            return None if cancellation.cancelled else repository.get_profile()

        operation: BackgroundOperation = load
        operation_id = self._runner.start(operation)
        self._operations[operation_id] = "load"
        self._set_busy(True)

    def save_profile(self) -> None:
        if self._save_service is None or self._busy():
            return
        try:
            tls_mode = TlsMode(self.tls_combo.currentData())
        except (TypeError, ValueError):
            self.status_label.setText("Selecione uma proteção TLS válida.")
            return
        host = self.host_input.text()
        port = self.port_input.value()
        sender = self.sender_input.text()
        recipient = self.recipient_input.text()
        username = self.username_input.text() or None
        password = self.password_input.text()
        sender_authorized = self.sender_check.isChecked()
        recipient_confirmed = self.recipient_check.isChecked()
        service = self._save_service

        def save(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> ProfileSaveResult:
            if cancellation.cancelled:
                raise RuntimeError("operation cancelled")
            return service.execute(
                host=host,
                port=port,
                tls_mode=tls_mode,
                sender=sender,
                recipient=recipient,
                username=username,
                password=password,
                sender_authorized=sender_authorized,
                recipient_confirmed=recipient_confirmed,
            )

        self._start("save", save, "Salvando perfil sem persistir a senha em arquivos…")

    def test_connection(self) -> None:
        if self._test_service is None or self._busy():
            return
        service = self._test_service

        def test(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> str:
            if cancellation.cancelled:
                raise RuntimeError("operation cancelled")
            service.execute()
            return "connected"

        self._start("test", test, "Testando conexão TLS sem enviar mensagem ou arquivo…")

    def remove_profile(self) -> None:
        if self._remove_service is None or self._busy():
            return
        answer = QMessageBox.question(
            self,
            "Remover perfil SMTP",
            "Remover o perfil local e solicitar a exclusão da credencial do cofre do Windows?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer is not QMessageBox.StandardButton.Yes:
            return
        service = self._remove_service

        def remove(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> bool:
            if cancellation.cancelled:
                raise RuntimeError("operation cancelled")
            return service.execute()

        self._start("remove", remove, "Removendo perfil e credencial…")

    def _start(self, kind: str, operation: BackgroundOperation, message: str) -> None:
        operation_id = self._runner.start(operation)
        self._operations[operation_id] = kind
        self._set_busy(True)
        self.status_label.setText(message)

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        kind = self._operations.get(operation_id)
        if kind is None:
            return
        if kind == "load":
            self._profile_loaded = True
            if isinstance(result, SmtpProfile):
                self._has_profile = True
                self._set_profile(result)
                self.profile_available_changed.emit(True)
                self.status_label.setText(
                    "Perfil SMTP local carregado. A autorização na Amazon é autodeclarada."
                )
            else:
                self._has_profile = False
                self.profile_available_changed.emit(False)
                self.status_label.setText(
                    "SMTP não configurado; o fluxo manual permanece disponível."
                )
        elif kind == "save" and isinstance(result, ProfileSaveResult):
            self._profile_loaded = True
            self._has_profile = True
            self.profile_available_changed.emit(True)
            self._set_profile(result.profile)
            self.password_input.clear()
            message = "Perfil SMTP salvo. Nenhuma conexão ou mensagem foi iniciada."
            if not result.previous_credential_removed:
                message += " Não foi possível limpar a credencial anterior do cofre do Windows."
            self.status_label.setText(message)
        elif kind == "test":
            self.status_label.setText(
                "Conexão TLS validada. Nenhuma mensagem ou arquivo foi enviado."
            )
        elif kind == "remove":
            self._profile_loaded = True
            self._has_profile = False
            self.profile_available_changed.emit(False)
            self._clear_profile()
            self.status_label.setText(
                "Perfil removido. O Windows informou que a credencial não pôde ser removida; "
                "verifique o Gerenciador de Credenciais."
                if result is False
                else "Perfil e credencial removidos do cofre do Windows."
            )
        self._operations.pop(operation_id, None)
        self._set_busy(False)

    def _on_failed(self, operation_id: str, code: str) -> None:
        kind = self._operations.get(operation_id)
        if kind is None:
            return
        message = {
            "SMTP_PROFILE_INVALID": "Revise os campos e as duas confirmações de autorização.",
            "CREDENTIAL_VAULT_UNAVAILABLE": "O cofre seguro do Windows não está disponível.",
            "CREDENTIAL_MISSING": "A senha não está mais no cofre. Informe-a novamente.",
            "TRANSFER_PERSISTENCE_FAILED": "Não foi possível salvar o perfil SMTP local.",
            "OPERATION_FAILED": "Não foi possível concluir a operação SMTP solicitada.",
        }.get(code, "Não foi possível concluir a operação SMTP solicitada.")
        self.password_input.clear()
        self.status_label.setText(message)
        self._operations.pop(operation_id, None)
        self._set_busy(False)

    def _on_cancelled(self, operation_id: str) -> None:
        if self._operations.pop(operation_id, None) is not None:
            self.password_input.clear()
            self._set_busy(False)
            self.status_label.setText("Operação SMTP cancelada.")

    def _on_finished(self, operation_id: str) -> None:
        if self._operations.pop(operation_id, None) is not None:
            self._set_busy(False)

    def _set_profile(self, profile: SmtpProfile) -> None:
        self.host_input.setText(profile.host)
        self.port_input.setValue(profile.port)
        self.tls_combo.setCurrentIndex(self.tls_combo.findData(profile.tls_mode.value))
        self.sender_input.setText(profile.sender)
        self.recipient_input.setText(profile.recipient)
        self.username_input.setText(profile.username or "")
        self.password_input.clear()
        self.sender_check.setChecked(profile.sender_authorized)
        self.recipient_check.setChecked(profile.recipient_confirmed)
        self.remove_button.setEnabled(True)
        if profile.credential_ref is not None:
            self.password_input.setPlaceholderText(
                "Senha guardada no cofre; deixe vazio para manter"
            )
        else:
            self.password_input.setPlaceholderText("Sem autenticação SMTP configurada")

    def _clear_profile(self) -> None:
        self.host_input.clear()
        self.port_input.setValue(587)
        self.tls_combo.setCurrentIndex(0)
        self.sender_input.clear()
        self.recipient_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.sender_check.setChecked(False)
        self.recipient_check.setChecked(False)
        self.remove_button.setEnabled(False)

    def _busy(self) -> bool:
        return bool(self._operations)

    def _set_busy(self, busy: bool) -> None:
        self.save_button.setEnabled(
            not busy and self.recipient_check.isChecked() and self.sender_check.isChecked()
        )
        self.test_button.setEnabled(not busy and self._profile_loaded and self._has_profile)
        self.remove_button.setEnabled(
            not busy and self._profile_loaded and self._has_profile
        )
        if busy:
            self.group.setProperty("busy", True)
        else:
            self.group.setProperty("busy", False)

    def _update_save_enabled(self, *_args: object) -> None:
        self.save_button.setEnabled(
            not self._busy()
            and self._profile_loaded
            and self.recipient_check.isChecked()
            and self.sender_check.isChecked()
        )

    def _clear_recipient_confirmation(self, _value: str) -> None:
        self.recipient_check.setChecked(False)

    def _clear_sender_confirmation(self, _value: str) -> None:
        self.sender_check.setChecked(False)
