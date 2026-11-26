"""Fila local real, sem iniciar operações para fontes não autorizadas."""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.downloads.controls import DownloadControls
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.downloads import DownloadChapterState, DownloadPageState
from manga_to_kindle.infrastructure.persistence.download_repository import (
    DownloadQueueSnapshot,
    DownloadRepository,
)
from manga_to_kindle.presentation.qt.views.components import EmptyState
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)

_STATE_LABELS = {
    DownloadState.QUEUED: "Na fila",
    DownloadState.RUNNING: "Em andamento",
    DownloadState.PAUSED: "Pausado",
    DownloadState.INTERRUPTED: "Interrompido",
    DownloadState.SUCCEEDED: "Concluído",
    DownloadState.FAILED: "Falha",
    DownloadState.CANCELLED: "Cancelado",
}
_CHAPTER_STATE_LABELS = {
    DownloadChapterState.QUEUED: "Na fila",
    DownloadChapterState.RUNNING: "Em andamento",
    DownloadChapterState.PARTIAL: "Parcial",
    DownloadChapterState.PAUSED: "Pausado",
    DownloadChapterState.INTERRUPTED: "Interrompido",
    DownloadChapterState.COMPLETE: "Concluído",
    DownloadChapterState.FAILED: "Falha",
    DownloadChapterState.CANCELLED: "Cancelado",
}
_PAGE_STATE_LABELS = {
    DownloadPageState.QUEUED: "Na fila",
    DownloadPageState.RUNNING: "Em andamento",
    DownloadPageState.STAGING: "Validando arquivo",
    DownloadPageState.WAITING_RETRY: "Aguardando nova tentativa",
    DownloadPageState.INTERRUPTED: "Interrompida",
    DownloadPageState.COMPLETE: "Concluída",
    DownloadPageState.FAILED: "Falha",
}


class DownloadsView(QWidget):
    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: DownloadRepository | None = None
        self._controls: DownloadControls | None = None
        self._resume_available = False
        self._operation_id: str | None = None
        self._jobs: dict[UUID, DownloadQueueSnapshot] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.empty_state = EmptyState(
            "Nenhuma fonte autorizada",
            "A fixture do catálogo não permite baixar páginas. Downloads serão habilitados "
            "quando houver um provedor com autorização, destinos e limites revisados. "
            "Nenhuma conexão será iniciada enquanto esse requisito não existir.",
            "Fonte sem autorização",
        )
        self.empty_state.action_button.setEnabled(False)
        self.empty_state.action_button.setAccessibleDescription(
            "Indisponível até existir um provedor autorizado para download local."
        )

        self.queue_status = QLabel("A fila local será consultada após a inicialização.")
        self.queue_status.setObjectName("downloadQueueStatus")
        self.queue_status.setAccessibleName("Estado da fila de downloads")
        self.queue_status.setWordWrap(True)
        self.chapter_progress = QLabel("Selecione um trabalho para ver o progresso por capítulo.")
        self.chapter_progress.setObjectName("downloadChapterProgress")
        self.chapter_progress.setAccessibleName("Progresso por capítulo")
        self.chapter_progress.setWordWrap(True)
        self.job_list = QListWidget()
        self.job_list.setObjectName("downloadJobList")
        self.job_list.setAccessibleName("Trabalhos locais de download")
        self.job_list.currentItemChanged.connect(self._selection_changed)
        self.page_list = QListWidget()
        self.page_list.setObjectName("downloadPageProgress")
        self.page_list.setAccessibleName("Progresso individual das páginas")
        self.page_list.setMaximumHeight(160)

        self.refresh_button = QPushButton("Atualizar fila")
        self.refresh_button.setObjectName("refreshDownloads")
        self.refresh_button.setAccessibleName("Atualizar trabalhos locais de download")
        self.refresh_button.setEnabled(False)
        self.pause_button = QPushButton("Pausar")
        self.pause_button.setObjectName("pauseDownload")
        self.pause_button.setAccessibleName("Pausar trabalho selecionado")
        self.pause_button.setEnabled(False)
        self.resume_button = QPushButton("Retomar")
        self.resume_button.setObjectName("resumeDownload")
        self.resume_button.setAccessibleName("Retomar trabalho selecionado")
        self.resume_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancelDownload")
        self.cancel_button.setAccessibleName("Cancelar trabalho selecionado")
        self.cancel_button.setEnabled(False)
        actions = QHBoxLayout()
        actions.addWidget(self.refresh_button)
        actions.addStretch(1)
        actions.addWidget(self.pause_button)
        actions.addWidget(self.resume_button)
        actions.addWidget(self.cancel_button)

        layout.addWidget(self.empty_state)
        layout.addWidget(self.queue_status)
        layout.addWidget(self.job_list, 1)
        layout.addWidget(self.chapter_progress)
        layout.addWidget(self.page_list)
        layout.addLayout(actions)
        self.job_list.hide()
        self.chapter_progress.hide()
        self.page_list.hide()
        self.refresh_button.clicked.connect(self.refresh)
        self.pause_button.clicked.connect(lambda: self._change_state("pause"))
        self.resume_button.clicked.connect(lambda: self._change_state("resume"))
        self.cancel_button.clicked.connect(lambda: self._change_state("cancel"))
        self._runner.succeeded.connect(self._operation_succeeded)
        self._runner.failed.connect(self._operation_failed)
        self._runner.finished.connect(self._operation_finished)

    def bind_queue(
        self,
        repository: DownloadRepository,
        controls: DownloadControls,
        *,
        resume_available: bool = False,
    ) -> None:
        self._repository = repository
        self._controls = controls
        self._resume_available = resume_available
        self.refresh_button.setEnabled(True)
        self.refresh()

    def refresh(self) -> None:
        repository = self._repository
        if repository is None or self._operation_id is not None:
            return

        def read_jobs(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> tuple[DownloadQueueSnapshot, ...]:
            return () if cancellation.cancelled else repository.list_snapshots()

        self.queue_status.setText("Lendo trabalhos locais…")
        self._start_operation(read_jobs)

    def _change_state(self, action: str) -> None:
        controls = self._controls
        item = self.job_list.currentItem()
        if controls is None or item is None or self._operation_id is not None:
            return
        job_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(job_id, UUID):
            return
        command = {
            "pause": controls.pause,
            "resume": controls.resume,
            "cancel": controls.cancel,
        }[action]

        def change_state(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> tuple[DownloadQueueSnapshot, ...]:
            if cancellation.cancelled:
                return ()
            command(job_id)
            repository = self._repository
            return repository.list_snapshots() if repository is not None else ()

        self.queue_status.setText("Salvando controle do trabalho…")
        self._start_operation(change_state)

    def _start_operation(self, operation: BackgroundOperation) -> None:
        self._operation_id = self._runner.start(operation)
        self.refresh_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def _operation_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id != self._operation_id or not isinstance(result, tuple):
            return
        snapshots = tuple(
            snapshot for snapshot in result if isinstance(snapshot, DownloadQueueSnapshot)
        )
        if len(snapshots) == len(result):
            self._render_jobs(snapshots)

    def _operation_failed(self, operation_id: str, code: str) -> None:
        if operation_id == self._operation_id:
            self.queue_status.setText(
                "Não foi possível ler a fila local. Tente atualizar novamente. "
                f"Código: {code}."
            )

    def _operation_finished(self, operation_id: str) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_id = None
        self.refresh_button.setEnabled(self._repository is not None)
        self._selection_changed()

    def _render_jobs(self, snapshots: tuple[DownloadQueueSnapshot, ...]) -> None:
        selected_id = self.job_list.currentItem().data(Qt.ItemDataRole.UserRole) if (
            self.job_list.currentItem() is not None
        ) else None
        self._jobs = {snapshot.job.id: snapshot for snapshot in snapshots}
        self.job_list.clear()
        for snapshot in snapshots:
            job = snapshot.job
            state_label = _STATE_LABELS[job.state]
            progress = f"{job.progress}/{job.total} páginas" if job.total is not None else (
                f"{job.progress} páginas concluídas; total desconhecido"
            )
            item = QListWidgetItem(
                f"Trabalho {str(job.id)[:8]}  ·  {state_label}  ·  {progress}"
            )
            item.setData(Qt.ItemDataRole.UserRole, job.id)
            self.job_list.addItem(item)
            if job.id == selected_id:
                self.job_list.setCurrentItem(item)
        has_jobs = bool(snapshots)
        self.empty_state.setVisible(not has_jobs)
        self.job_list.setVisible(has_jobs)
        if has_jobs:
            self.queue_status.setText(
                "Os trabalhos ficam salvos localmente. Após reiniciar, um trabalho interrompido "
                "não inicia tráfego sem uma ação explícita."
            )
        else:
            self.queue_status.setText(
                "Fila vazia. A consulta de catálogo não concede autorização para baixar páginas."
            )
        self._selection_changed()

    def _selection_changed(self, *_args: object) -> None:
        item = self.job_list.currentItem()
        job_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        snapshot = self._jobs.get(job_id) if isinstance(job_id, UUID) else None
        job = snapshot.job if snapshot is not None else None
        busy = self._operation_id is not None
        if snapshot is None:
            self.chapter_progress.clear()
            self.page_list.clear()
            self.chapter_progress.hide()
            self.page_list.hide()
        else:
            chapters = "  ·  ".join(
                f"Capítulo {chapter.position + 1}: {chapter.page_completed}/"
                f"{chapter.page_total if chapter.page_total is not None else '—'} páginas "
                f"({_CHAPTER_STATE_LABELS[chapter.state]})"
                for chapter in snapshot.chapter_progress
            )
            self.chapter_progress.setText(chapters)
            self.chapter_progress.show()
            self.page_list.clear()
            chapter_positions = {
                chapter.chapter_id: chapter.position + 1
                for chapter in snapshot.chapter_progress
            }
            for page in snapshot.pages:
                self.page_list.addItem(
                    f"Capítulo {chapter_positions[page.chapter_id]}  ·  "
                    f"Página {page.position + 1}: {_PAGE_STATE_LABELS[page.state]}"
                )
            self.page_list.setVisible(bool(snapshot.pages))
        self.pause_button.setEnabled(
            not busy and job is not None and job.state is DownloadState.RUNNING
        )
        self.resume_button.setEnabled(
            not busy
            and self._resume_available
            and job is not None
            and job.state in {DownloadState.PAUSED, DownloadState.INTERRUPTED}
        )
        self.cancel_button.setEnabled(
            not busy
            and job is not None
            and job.state not in {
                DownloadState.SUCCEEDED,
                DownloadState.FAILED,
                DownloadState.CANCELLED,
            }
        )
