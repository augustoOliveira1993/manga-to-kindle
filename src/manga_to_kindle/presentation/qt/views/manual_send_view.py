"""Fluxo manual: verificar um EPUB local e abrir a pasta e a página oficial."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.transfers.open_manual_flow import (
    OpenManualSend,
    SEND_TO_KINDLE_URL,
)
from manga_to_kindle.domain.transfers import ExportTransferArtifact, ManualFlowResult
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)


class ManualTransferRepository(Protocol):
    def list_transfer_artifacts(self) -> tuple[ExportTransferArtifact, ...]: ...


class ManualSendView(QWidget):
    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: ManualTransferRepository | None = None
        self._workflow: OpenManualSend | None = None
        self._artifacts: dict[UUID, ExportTransferArtifact] = {}
        self._load_operation_id: str | None = None
        self._open_operation_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        intro = QLabel(
            "Escolha um EPUB exportado e validado. O aplicativo apenas abre a pasta e a "
            "página oficial; você seleciona o arquivo e confirma qualquer envio no site."
        )
        intro.setObjectName("manualSendIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.artifact_combo = QComboBox()
        self.artifact_combo.setObjectName("manualSendArtifact")
        self.artifact_combo.setAccessibleName("EPUB local para envio manual ao Kindle")
        self.artifact_combo.addItem("Carregue uma exportação local", None)
        layout.addWidget(self.artifact_combo)

        self.path_label = QLabel("Pasta local: nenhuma exportação selecionada")
        self.path_label.setObjectName("manualSendPath")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.url_label = QLabel(f"Página oficial: {SEND_TO_KINDLE_URL}")
        self.url_label.setObjectName("manualSendUrl")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_label.setWordWrap(True)
        layout.addWidget(self.url_label)

        self.status_label = QLabel("Nenhum envio foi iniciado.")
        self.status_label.setObjectName("manualSendStatus")
        self.status_label.setAccessibleName("Estado do fluxo manual Send to Kindle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.refresh_button = QPushButton("Atualizar exportações")
        self.refresh_button.setObjectName("refreshManualExports")
        self.open_button = QPushButton("Abrir no Send to Kindle")
        self.open_button.setObjectName("openManualSend")
        self.open_button.setProperty("primaryAction", True)
        self.open_button.setEnabled(False)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.open_button)
        layout.addStretch(1)

        self.refresh_button.clicked.connect(self.refresh)
        self.open_button.clicked.connect(self.open_selected)
        self.artifact_combo.currentIndexChanged.connect(self._selection_changed)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.failed.connect(self._on_failed)
        self._runner.cancelled.connect(self._on_cancelled)
        self._runner.finished.connect(self._on_finished)

    def bind_services(
        self,
        repository: ManualTransferRepository,
        workflow: OpenManualSend,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self.refresh()

    def refresh(self) -> None:
        if self._repository is None or self._load_operation_id is not None:
            return
        repository = self._repository

        def load(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> tuple[ExportTransferArtifact, ...]:
            if cancellation.cancelled:
                return ()
            return repository.list_transfer_artifacts()

        operation: BackgroundOperation = load
        self._load_operation_id = self._runner.start(operation)
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Consultando EPUBs exportados localmente…")

    def open_selected(self) -> None:
        if self._workflow is None or self._open_operation_id is not None:
            return
        artifact_id = self.artifact_combo.currentData()
        if not isinstance(artifact_id, UUID):
            return
        workflow = self._workflow

        def open_flow(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> ManualFlowResult:
            if cancellation.cancelled:
                raise RuntimeError("A ação foi cancelada antes da verificação.")
            return workflow.execute(artifact_id)

        operation: BackgroundOperation = open_flow
        self._open_operation_id = self._runner.start(operation)
        self.open_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Verificando checksum antes de abrir o fluxo manual…")

    def _selection_changed(self, *_args: object) -> None:
        artifact_id = self.artifact_combo.currentData()
        artifact = self._artifacts.get(artifact_id) if isinstance(artifact_id, UUID) else None
        if artifact is None:
            self.path_label.setText("Pasta local: nenhuma exportação selecionada")
            self.open_button.setEnabled(False)
            return
        self.path_label.setText(f"Pasta local: {artifact.path.parent}")
        self.open_button.setEnabled(self._open_operation_id is None)

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id == self._load_operation_id:
            if isinstance(result, tuple) and all(
                isinstance(item, ExportTransferArtifact) for item in result
            ):
                self._set_artifacts(result)
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
            self.status_label.setText(
                "Selecione um EPUB validado. Os formatos, o limite e a conversão no serviço "
                "externo podem mudar."
                if self._artifacts
                else "Nenhum EPUB exportado localmente foi encontrado."
            )
            return
        if operation_id != self._open_operation_id or not isinstance(result, ManualFlowResult):
            return
        failures: list[str] = []
        if not result.directory_opened:
            failures.append("Não foi possível abrir a pasta local.")
        if not result.page_opened:
            failures.append("Não foi possível abrir a página Send to Kindle.")
        if failures:
            self.status_label.setText(
                " ".join(failures)
                + " O caminho e o link oficial acima podem ser copiados para uma ação manual."
            )
        else:
            self.status_label.setText(
                "Pasta e página oficial abertas. Selecione o EPUB e conclua o envio manualmente."
            )
        self._open_operation_id = None
        self.refresh_button.setEnabled(True)
        self._selection_changed()

    def _on_failed(self, operation_id: str, code: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
            self.status_label.setText("Não foi possível consultar exportações locais.")
        elif operation_id == self._open_operation_id:
            self._open_operation_id = None
            self.refresh_button.setEnabled(True)
            self._selection_changed()
            self.status_label.setText(
                "O EPUB está ausente, alterado ou não passou pela validação local. "
                f"Nenhuma abertura foi solicitada ({code})."
            )

    def _on_cancelled(self, operation_id: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
        elif operation_id == self._open_operation_id:
            self._open_operation_id = None
            self.refresh_button.setEnabled(True)
            self._selection_changed()
            self.status_label.setText("A verificação foi cancelada antes de abrir a página.")

    def _on_finished(self, operation_id: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
        if operation_id == self._open_operation_id:
            self._open_operation_id = None
            self.refresh_button.setEnabled(True)
            self._selection_changed()

    def _set_artifacts(self, artifacts: tuple[ExportTransferArtifact, ...]) -> None:
        self._artifacts = {artifact.id: artifact for artifact in artifacts}
        self.artifact_combo.blockSignals(True)
        self.artifact_combo.clear()
        self.artifact_combo.addItem("Selecione um EPUB", None)
        for artifact in artifacts:
            if artifact.format != "epub":
                continue
            self.artifact_combo.addItem(
                f"{artifact.path.name} · {artifact.size_bytes / (1024 * 1024):.2f} MiB",
                artifact.id,
            )
        self.artifact_combo.blockSignals(False)
        self._selection_changed()
