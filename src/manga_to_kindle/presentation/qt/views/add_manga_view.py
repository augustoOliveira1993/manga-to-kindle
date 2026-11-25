"""Formulário local que valida URL sem consultar ou registrar a fonte."""

from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.catalog.chapter_selection import ChapterSelection
from manga_to_kindle.application.providers.resolve_provider import (
    provider_error_message_for_code,
)
from manga_to_kindle.application.ui.validate_url import validate_http_url
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.presentation.qt.view_models import DemoOutcome, resolve_demo_outcome
from manga_to_kindle.presentation.qt.views.components import ChapterSelectionList
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner
from manga_to_kindle.presentation.qt.workers.demo import CatalogQuery, make_catalog_operation


class AddMangaView(QWidget):
    def __init__(
        self,
        runner: OperationRunner,
        catalog_query: CatalogQuery | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._catalog_query = catalog_query
        self._operation_id: str | None = None
        self._outcome = DemoOutcome.SUCCESS
        self._chapters: tuple[Chapter, ...] = ()
        self._selection = ChapterSelection()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        intro = QLabel(
            "Informe um endereço para testar a validação local. Nenhuma conexão será feita."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setObjectName("mangaUrlInput")
        self.url_input.setPlaceholderText("https://exemplo.com/manga/...")
        self.url_input.setAccessibleName("Endereço HTTP ou HTTPS para demonstração")
        form.addRow("Endereço HTTP/HTTPS", self.url_input)
        self.outcome_combo = QComboBox()
        self.outcome_combo.setObjectName("catalogDemoOutcome")
        self.outcome_combo.setAccessibleName("Resultado da consulta simulada")
        self.outcome_combo.addItem("Catálogo de demonstração disponível", DemoOutcome.SUCCESS)
        self.outcome_combo.addItem("Nenhum capítulo na demonstração", DemoOutcome.EMPTY)
        self.outcome_combo.addItem("Simular falha de consulta", DemoOutcome.ERROR)
        form.addRow("Resultado simulado", self.outcome_combo)

        self.query_button = QPushButton("Consultar demonstração")
        self.query_button.setObjectName("queryDemoCatalog")
        self.query_button.setAccessibleName("Consultar catálogo de demonstração, sem rede")
        self.query_button.setProperty("primaryAction", True)
        self.status_label = QLabel("Aguardando endereço para demonstração.")
        self.status_label.setObjectName("catalogState")
        self.status_label.setAccessibleName("Estado da consulta")
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("catalogProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setAccessibleName("Progresso da consulta simulada")
        self.progress_bar.hide()

        selection_header = QHBoxLayout()
        self.catalog_title = QLabel("Catálogo")
        self.catalog_title.setStyleSheet("font-size: 16px; font-weight: 650;")
        self.catalog_metadata = QLabel("Autor: Não informado  ·  Idioma: Não informado")
        self.catalog_metadata.setObjectName("catalogMetadata")
        self.catalog_metadata.setWordWrap(True)
        self.cover_placeholder = QLabel("Capa não informada")
        self.cover_placeholder.setObjectName("catalogCoverPlaceholder")
        self.cover_placeholder.setAccessibleName("Capa não informada")
        self.cover_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selection_summary = QLabel("0 capítulos selecionados")
        self.selection_summary.setObjectName("chapterSelectionSummary")
        self.selection_summary.setAccessibleName("Quantidade de capítulos selecionados")
        selection_header.addWidget(self.catalog_title)
        selection_header.addStretch(1)
        selection_header.addWidget(self.selection_summary)
        self.chapter_list = ChapterSelectionList()
        self.chapter_list.setMinimumHeight(190)
        self.chapter_list.hide()
        self.chapter_list.selection_changed.connect(self._selection_changed)
        self.select_all_button = QPushButton("Selecionar todos")
        self.select_all_button.setObjectName("selectAllChapters")
        self.select_all_button.clicked.connect(self._select_all)
        self.select_none_button = QPushButton("Limpar seleção")
        self.select_none_button.setObjectName("clearChapterSelection")
        self.select_none_button.clicked.connect(self._select_none)
        self.range_start_combo = QComboBox()
        self.range_start_combo.setAccessibleName("Primeiro capítulo do intervalo")
        self.range_end_combo = QComboBox()
        self.range_end_combo.setAccessibleName("Último capítulo do intervalo")
        self.select_range_button = QPushButton("Selecionar intervalo inclusivo")
        self.select_range_button.setObjectName("selectChapterRange")
        self.select_range_button.clicked.connect(self._select_range)
        range_actions = QHBoxLayout()
        range_actions.addWidget(self.range_start_combo)
        range_actions.addWidget(self.range_end_combo)
        range_actions.addWidget(self.select_range_button)
        selection_actions = QHBoxLayout()
        selection_actions.addWidget(self.select_all_button)
        selection_actions.addWidget(self.select_none_button)
        selection_actions.addStretch(1)
        self.selection_widget = QWidget()
        selection_layout = QVBoxLayout(self.selection_widget)
        selection_layout.setContentsMargins(0, 8, 0, 0)
        selection_layout.addLayout(selection_header)
        selection_layout.addWidget(self.catalog_metadata)
        selection_layout.addWidget(self.cover_placeholder)
        selection_layout.addWidget(self.chapter_list)
        selection_layout.addLayout(range_actions)
        selection_layout.addLayout(selection_actions)
        self.selection_widget.hide()

        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.query_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.selection_widget, 1)

        self.query_button.clicked.connect(self.query_demo)
        runner.started.connect(self._on_started)
        runner.progress.connect(self._on_progress)
        runner.succeeded.connect(self._on_succeeded)
        runner.failed.connect(self._on_failed)
        runner.cancelled.connect(self._on_cancelled)
        runner.finished.connect(self._on_finished)

    @property
    def selected_chapter_ids(self) -> tuple[UUID, ...]:
        return self.chapter_list.selected_chapter_ids()

    @property
    def operation_id(self) -> str | None:
        return self._operation_id

    @property
    def operation_runner(self) -> OperationRunner:
        return self._runner

    def set_catalog_query(self, catalog_query: CatalogQuery | None) -> None:
        self._catalog_query = catalog_query

    def query_demo(self) -> None:
        if self._operation_id is not None:
            return
        validation = validate_http_url(self.url_input.text())
        if not validation.valid:
            self.status_label.setText(
                "Endereço inválido. Informe uma URL HTTP ou HTTPS sem credenciais."
            )
            self.progress_bar.hide()
            self.chapter_list.hide()
            self.selection_widget.hide()
            return
        if self._catalog_query is None:
            self.status_label.setText("O provedor de catálogo ainda não está disponível.")
            return
        self._outcome = resolve_demo_outcome(self.outcome_combo.currentData())
        self.query_button.setEnabled(False)
        self.status_label.setText("Consultando catálogo de demonstração…")
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.chapter_list.hide()
        self.selection_widget.hide()
        self._operation_id = self._runner.start(
            make_catalog_operation(
                self._catalog_query,
                self.url_input.text().strip(),
                self._outcome,
                total_steps=8,
            )
        )

    def _select_range(self) -> None:
        first_id = self.range_start_combo.currentData()
        last_id = self.range_end_combo.currentData()
        if not isinstance(first_id, UUID) or not isinstance(last_id, UUID):
            return
        ordered_ids = tuple(chapter.id for chapter in self._chapters)
        self._selection.select_range(first_id, last_id, ordered_ids)
        self.chapter_list.set_selected_ids(self._selection.selected_ids)

    def _selection_changed(self, chapter_ids: tuple[UUID, ...]) -> None:
        self._selection.replace(chapter_ids)
        count = len(chapter_ids)
        self.selection_summary.setText(
            f"{count} capítulo selecionado" if count == 1 else f"{count} capítulos selecionados"
        )

    def _select_all(self) -> None:
        for row in range(self.chapter_list.count()):
            item = self.chapter_list.item(row)
            item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        for row in range(self.chapter_list.count()):
            item = self.chapter_list.item(row)
            item.setCheckState(Qt.CheckState.Unchecked)

    def _show_catalog(self, snapshot: CatalogSnapshot) -> None:
        self._chapters = snapshot.chapters
        chapter_ids = tuple(chapter.id for chapter in self._chapters)
        self._selection.reconcile(chapter_ids)
        self.catalog_title.setText(snapshot.manga.title)
        author = snapshot.manga.author or "Não informado"
        language = snapshot.manga.language or "Não informado"
        self.catalog_metadata.setText(f"Autor: {author}  ·  Idioma: {language}")
        self.cover_placeholder.setText(
            "Capa não informada"
            if snapshot.manga.cover_path is None
            else f"Capa local: {snapshot.manga.cover_path.name}"
        )
        self.chapter_list.set_chapters(self._chapters, self._selection.selected_ids)
        for combo in (self.range_start_combo, self.range_end_combo):
            combo.clear()
            for chapter in self._chapters:
                title = chapter.title or (
                    str(chapter.number) if chapter.number is not None else "Especial"
                )
                combo.addItem(title, chapter.id)
        self.chapter_list.show()
        self.selection_widget.show()
        self.status_label.setText(
            "Catálogo de demonstração carregado. Nenhuma fonte real foi consultada."
            if snapshot.simulated
            else "Catálogo carregado."
        )
        self._selection_changed(self.chapter_list.selected_chapter_ids())

    def _on_started(self, operation_id: str) -> None:
        if operation_id == self._operation_id:
            self.status_label.setText("Carregando demonstração local…")

    def _on_progress(
        self,
        operation_id: str,
        completed: int,
        total: int | None,
        stage: str,
    ) -> None:
        if operation_id != self._operation_id:
            return
        if total:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(completed, total))
        else:
            self.progress_bar.setRange(0, 0)
        self.status_label.setText(f"{stage}: {completed} de {total or 'várias'}")

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id != self._operation_id:
            return
        if result is None:
            self.status_label.setText(
                "Demonstração concluída sem capítulos. Nenhum serviço foi consultado."
            )
            self.chapter_list.clear()
            self.selection_widget.hide()
            return
        if isinstance(result, CatalogSnapshot):
            self._show_catalog(result)
        else:
            self._on_failed(operation_id, "PROVIDER_RESPONSE_INVALID")

    def _on_failed(self, operation_id: str, error_code: str) -> None:
        if operation_id == self._operation_id:
            if error_code == "DEMO_OPERATION_FAILED":
                message = "Falha simulada ao consultar. Tente novamente."
            else:
                message = provider_error_message_for_code(error_code)
            self.status_label.setText(message)
            self.chapter_list.hide()
            self.selection_widget.hide()

    def _on_cancelled(self, operation_id: str) -> None:
        if operation_id == self._operation_id:
            self.status_label.setText("Consulta simulada cancelada.")

    def _on_finished(self, operation_id: str) -> None:
        if operation_id != self._operation_id:
            return
        self._operation_id = None
        self.query_button.setEnabled(True)
        self.progress_bar.hide()

