"""Peças visuais compartilhadas por páginas da interface."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.presentation.qt.view_models import (
    DemoOutcome,
    DemoResult,
    resolve_demo_outcome,
)
from manga_to_kindle.presentation.qt.workers.adapter import BackgroundOperation, OperationRunner
from manga_to_kindle.presentation.qt.workers.demo import make_demo_operation


class SimulationBanner(QLabel):
    def __init__(self) -> None:
        super().__init__("DADOS SIMULADOS  •  serviços reais ainda não conectados")
        self.setObjectName("simulationBanner")
        self.setAccessibleName("Aviso: dados simulados, serviços reais ainda não conectados")
        self.setWordWrap(True)


class ChapterSelectionList(QListWidget):
    selection_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chapterSelectionList")
        self.setAccessibleName("Capítulos simulados; Espaço seleciona ou desmarca")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.itemChanged.connect(self._emit_selection)

    def set_chapters(
        self,
        chapters: Sequence[Chapter],
        selected_ids: frozenset[UUID] = frozenset(),
    ) -> None:
        was_blocked = self.blockSignals(True)
        self.clear()
        for chapter in chapters:
            number = f"{chapter.number}" if chapter.number is not None else "Especial"
            title = chapter.title or "Sem título informado"
            details = [f"Capítulo {number}  ·  {title}"]
            if chapter.volume is not None:
                details.append(f"Volume {chapter.volume}")
            if chapter.available is not None:
                details.append("Disponível" if chapter.available else "Indisponível")
            item = QListWidgetItem("  ·  ".join(details))
            item.setData(Qt.ItemDataRole.UserRole, chapter.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked if chapter.id in selected_ids else Qt.CheckState.Unchecked
            )
            self.addItem(item)
        self.blockSignals(was_blocked)
        self._emit_selection()

    def set_selected_ids(self, selected_ids: frozenset[UUID]) -> None:
        was_blocked = self.blockSignals(True)
        for row in range(self.count()):
            item = self.item(row)
            chapter_id = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(chapter_id, UUID):
                item.setCheckState(
                    Qt.CheckState.Checked
                    if chapter_id in selected_ids
                    else Qt.CheckState.Unchecked
                )
        self.blockSignals(was_blocked)
        self._emit_selection()

    def selected_chapter_ids(self) -> tuple[UUID, ...]:
        selected: list[UUID] = []
        for row in range(self.count()):
            item = self.item(row)
            chapter_id = item.data(Qt.ItemDataRole.UserRole)
            if item.checkState() is Qt.CheckState.Checked and isinstance(chapter_id, UUID):
                selected.append(chapter_id)
        return tuple(selected)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt override
        if event.key() == Qt.Key.Key_Space:
            self._toggle_current_item()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        item = self.itemAt(event.position().toPoint())
        if item is None or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setCurrentItem(item)
        self._toggle_item(item)
        event.accept()

    def _toggle_current_item(self) -> None:
        item = self.currentItem()
        if item is not None:
            self._toggle_item(item)

    def _toggle_item(self, item: QListWidgetItem) -> None:
        state = (
            Qt.CheckState.Unchecked
            if item.checkState() is Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(state)

    def _emit_selection(self, _: QListWidgetItem | None = None) -> None:
        self.selection_changed.emit(self.selected_chapter_ids())


class DemoJobPanel(QFrame):
    """Painel de progresso reutilizado por Downloads e Conversão simulados."""

    def __init__(
        self,
        runner: OperationRunner,
        *,
        action_text: str,
        summary: str,
        include_empty_outcome: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("jobPanel")
        self._runner = runner
        self._summary = summary
        self._operation_id: str | None = None
        self._can_start = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title = QLabel("Demonstração da operação")
        title.setStyleSheet("font-size: 16px; font-weight: 650;")
        self.status_label = QLabel("Nenhuma operação simulada em andamento.")
        self.status_label.setObjectName("demoJobStatus")
        self.status_label.setAccessibleName("Estado da operação simulada")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("demoJobProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAccessibleName("Progresso da operação simulada")
        self.progress_bar.setFormat("Aguardando demonstração")

        controls = QHBoxLayout()
        self.outcome_combo = QComboBox()
        self.outcome_combo.setObjectName("demoOutcome")
        self.outcome_combo.setAccessibleName("Resultado da demonstração")
        self.outcome_combo.addItem("Simular sucesso", DemoOutcome.SUCCESS)
        self.outcome_combo.addItem("Simular falha", DemoOutcome.ERROR)
        if include_empty_outcome:
            self.outcome_combo.addItem("Simular lista vazia", DemoOutcome.EMPTY)
        self.start_button = QPushButton(action_text)
        self.start_button.setObjectName("startDemoOperation")
        self.start_button.setAccessibleName(action_text)
        self.start_button.setProperty("primaryAction", True)
        self.cancel_button = QPushButton("Cancelar demonstração")
        self.cancel_button.setObjectName("cancelDemoOperation")
        self.cancel_button.setAccessibleName("Cancelar demonstração em andamento")
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.outcome_combo, 1)
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(controls)
        self.start_button.clicked.connect(self.start_demo)
        self.cancel_button.clicked.connect(self.cancel_demo)
        runner.started.connect(self._on_started)
        runner.progress.connect(self._on_progress)
        runner.succeeded.connect(self._on_succeeded)
        runner.failed.connect(self._on_failed)
        runner.cancelled.connect(self._on_cancelled)
        runner.finished.connect(self._on_finished)

    @property
    def operation_id(self) -> str | None:
        return self._operation_id

    @property
    def operation_runner(self) -> OperationRunner:
        return self._runner

    def set_can_start(self, enabled: bool) -> None:
        self._can_start = enabled
        self.start_button.setEnabled(enabled and self._operation_id is None)

    def start_demo(self) -> None:
        outcome = resolve_demo_outcome(self.outcome_combo.currentData())
        self.start_operation(make_demo_operation(outcome, summary=self._summary))

    def start_operation(self, operation: BackgroundOperation) -> None:
        if self._operation_id is not None or not self._can_start:
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Preparando demonstração")
        self.status_label.setText("Operação simulada em andamento…")
        self._operation_id = self._runner.start(operation)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def cancel_demo(self) -> None:
        if self._operation_id is not None and self._runner.cancel(self._operation_id):
            self.status_label.setText("Cancelamento solicitado…")
            self.cancel_button.setEnabled(False)

    def _on_started(self, operation_id: str) -> None:
        if operation_id == self._operation_id:
            self.status_label.setText("Operação simulada em andamento…")

    def _on_progress(
        self,
        operation_id: str,
        completed: int,
        total: int | None,
        stage: str,
    ) -> None:
        if operation_id != self._operation_id:
            return
        if total is None or total == 0:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Em andamento")
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(completed, total))
            self.progress_bar.setFormat(f"{completed} de {total}")
        self.status_label.setText(f"{stage} — {completed} de {total or 'várias'}")

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id != self._operation_id:
            return
        summary = result.summary if isinstance(result, DemoResult) else self._summary
        self.status_label.setText(f"{summary} Nenhum arquivo foi gerado.")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Demonstração concluída")

    def _on_failed(self, operation_id: str, code: str) -> None:
        if operation_id != self._operation_id:
            return
        if code == "OUTPUT_DIRECTORY_UNAVAILABLE":
            message = (
                "A pasta escolhida não está disponível. Escolha outra; "
                "nenhum arquivo foi alterado."
            )
        else:
            message = "Falha simulada. Tente novamente; nenhum arquivo foi alterado."
        self.status_label.setText(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Demonstração com falha")

    def _on_cancelled(self, operation_id: str) -> None:
        if operation_id == self._operation_id:
            self.status_label.setText("Demonstração cancelada. Nenhum arquivo foi alterado.")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat("Demonstração cancelada")

    def _on_finished(self, operation_id: str) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_id = None
        self.start_button.setEnabled(self._can_start)
        self.cancel_button.setEnabled(False)


class EmptyState(QFrame):
    action_requested = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        action_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 17px; font-weight: 650;")
        heading.setWordWrap(True)
        body = QLabel(description)
        body.setObjectName("muted")
        body.setWordWrap(True)
        self.action_button = QPushButton(action_text)
        self.action_button.setAccessibleName(action_text)
        self.action_button.clicked.connect(self.action_requested.emit)
        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignLeft)

