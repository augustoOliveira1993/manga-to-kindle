"""Histórico local de SMTP sem destinatários completos nem conteúdo do EPUB."""

from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from manga_to_kindle.domain.transfers import TransferHistoryItem, TransferState
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)


class TransferHistoryRepository(Protocol):
    def list_history(self, *, limit: int = 100) -> tuple[TransferHistoryItem, ...]: ...


class TransferHistoryView(QWidget):
    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: TransferHistoryRepository | None = None
        self._load_operation_id: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        intro = QLabel(
            "O histórico registra somente tentativas por e-mail. Aceitação SMTP não confirma "
            "conversão nem entrega ao Kindle."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.items = QListWidget()
        self.items.setObjectName("transferHistoryList")
        self.items.setAccessibleName("Histórico local de tentativas SMTP")
        layout.addWidget(self.items, 1)
        self.status_label = QLabel("Nenhuma tentativa SMTP registrada.")
        self.status_label.setObjectName("transferHistoryStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.refresh_button = QPushButton("Atualizar histórico")
        self.refresh_button.setObjectName("refreshTransferHistory")
        layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.failed.connect(self._on_failed)
        self._runner.finished.connect(self._on_finished)

    def bind_repository(self, repository: TransferHistoryRepository) -> None:
        self._repository = repository
        self.refresh()

    def refresh(self) -> None:
        if self._repository is None or self._load_operation_id is not None:
            return
        repository = self._repository

        def load(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> tuple[TransferHistoryItem, ...]:
            if cancellation.cancelled:
                return ()
            return repository.list_history()

        operation: BackgroundOperation = load
        self._load_operation_id = self._runner.start(operation)
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Lendo histórico SMTP local…")

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id != self._load_operation_id:
            return
        self._load_operation_id = None
        self.refresh_button.setEnabled(True)
        if not isinstance(result, tuple) or not all(
            isinstance(item, TransferHistoryItem) for item in result
        ):
            self.status_label.setText("O histórico não retornou registros válidos.")
            return
        self.items.clear()
        for item in result:
            self.items.addItem(_history_label(item))
        self.status_label.setText(
            f"{len(result)} tentativa(s) local(is). O aplicativo não monitora a conta Amazon."
            if result
            else "Nenhuma tentativa SMTP registrada."
        )

    def _on_failed(self, operation_id: str, _code: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
            self.status_label.setText("Não foi possível carregar o histórico SMTP local.")

    def _on_finished(self, operation_id: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)


def _history_label(item: TransferHistoryItem) -> str:
    job = item.job
    created = job.created_at
    if created.tzinfo is None:
        from datetime import UTC

        created = created.replace(tzinfo=UTC)
    local_time = created.astimezone().strftime("%d/%m/%Y %H:%M")
    if job.state is TransferState.ACCEPTED_BY_SMTP:
        outcome = "Aceito pelo servidor SMTP — entrega ao Kindle não confirmada"
    elif job.state is TransferState.REJECTED_TEMPORARY:
        outcome = "Recusa temporária do servidor SMTP"
    elif job.state is TransferState.REJECTED_PERMANENT:
        outcome = "Recusa do servidor SMTP"
    elif job.state is TransferState.UNKNOWN:
        outcome = "Resultado desconhecido — sem repetição automática"
    elif job.state is TransferState.CANCELLED_BEFORE_SUBMISSION:
        outcome = "Cancelado antes da submissão"
    elif job.state is TransferState.INTERRUPTED:
        outcome = "Interrompido antes da transmissão"
    else:
        outcome = "Falha antes da aceitação SMTP"
    return (
        f"{local_time} · {item.filename}\n"
        f"E-mail · {job.masked_recipient} · {outcome}"
    )
