"""Exporta páginas locais processadas em EPUB ou CBZ, sem enviar arquivos."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.exports.create_export import CreateExport, ExportResult
from manga_to_kindle.application.exports.ports import ExportRepositoryPort
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import (
    ExportableChapter,
    ExportFormat,
    ExportGrouping,
    ExportRequest,
)
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)

_ERROR_MESSAGES = {
    "EXPORT_PLAN_REJECTED": "A seleção não atende aos requisitos de exportação local.",
    "EXPORT_SOURCE_UNAVAILABLE": "Uma página deixou de estar disponível ou processada.",
    "EXPORT_OUTPUT_CONFLICT": (
        "Um arquivo com esse nome já existe. Escolha outra pasta; nenhum arquivo foi substituído."
    ),
    "EXPORT_OUTPUT_FAILED": "A pasta de saída não está disponível com segurança.",
    "EXPORT_PACKAGE_TOO_LARGE": "Um pacote excedeu o limite. Aumente-o e tente novamente.",
    "EPUB_VALIDATION_FAILED": "O EPUB não passou pela validação estrutural local.",
    "CBZ_VALIDATION_FAILED": "O CBZ não passou pela validação de páginas e ordem.",
    "EXPORT_CANCELLED": "Exportação cancelada; arquivos de origem preservados.",
}


class ConversionView(QWidget):
    manual_send_requested = Signal()

    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: ExportRepositoryPort | None = None
        self._workflow: CreateExport | None = None
        self._chapters: tuple[ExportableChapter, ...] = ()
        self._pending_selected_ids: tuple[UUID, ...] = ()
        self._load_operation_id: str | None = None
        self._export_operation_id: str | None = None

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.content_scroll_area = QScrollArea(self)
        self.content_scroll_area.setObjectName("conversionScrollArea")
        self.content_scroll_area.setWidgetResizable(True)
        self.content_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(self.content_scroll_area)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        intro = QLabel(
            "Crie cópias locais a partir das páginas importadas e processadas. "
            "Nada é enviado ao Kindle ou à rede. EPUB fixo ainda requer validação manual "
            "no leitor; KCC não está configurado."
        )
        intro.setObjectName("conversionIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.chapter_list = QListWidget()
        self.chapter_list.setObjectName("exportableChapterList")
        self.chapter_list.setAccessibleName("Capítulos locais prontos para exportação")
        self.chapter_list.setMinimumHeight(130)
        self.chapter_list.itemChanged.connect(self._selection_changed)
        layout.addWidget(self.chapter_list)

        self.selection_label = QLabel("Nenhum capítulo pronto para exportação")
        self.selection_label.setObjectName("conversionSelection")
        self.selection_label.setAccessibleName("Capítulos selecionados para exportação")
        layout.addWidget(self.selection_label)

        form = QFormLayout()
        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setObjectName("conversionOutputPath")
        self.output_path.setReadOnly(True)
        self.output_path.setPlaceholderText("Selecione uma pasta de saída")
        self.output_path.setAccessibleName("Pasta local escolhida para exportação")
        self.choose_folder_button = QPushButton("Escolher pasta…")
        self.choose_folder_button.setObjectName("chooseOutputFolder")
        self.choose_folder_button.setAccessibleName("Escolher pasta local de saída")
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(self.choose_folder_button)
        form.addRow("Pasta de saída", output_row)

        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("conversionProfile")
        self.profile_combo.setAccessibleName("Perfil de saída das imagens processadas")
        self.profile_combo.addItem("Selecione um perfil", None)
        self.profile_combo.addItem("600 × 800 — páginas processadas em F006", "processed-600x800")
        form.addRow("Perfil de saída", self.profile_combo)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("conversionFormat")
        self.format_combo.setAccessibleName("Formato de arquivo local")
        self.format_combo.addItem("EPUB 3 — layout fixo", ExportFormat.EPUB.value)
        self.format_combo.addItem("CBZ — páginas processadas", ExportFormat.CBZ.value)
        form.addRow("Formato", self.format_combo)

        self.grouping_combo = QComboBox()
        self.grouping_combo.setObjectName("conversionGrouping")
        self.grouping_combo.setAccessibleName("Agrupamento dos arquivos exportados")
        self.grouping_combo.addItem("Um arquivo por capítulo", ExportGrouping.CHAPTER.value)
        self.grouping_combo.addItem("Agrupar por volume conhecido", ExportGrouping.VOLUME.value)
        form.addRow("Agrupamento", self.grouping_combo)

        self.direction_combo = QComboBox()
        self.direction_combo.setObjectName("conversionDirection")
        self.direction_combo.setAccessibleName("Direção declarada no EPUB")
        self.direction_combo.addItem(
            "Direita para esquerda (RTL)", ReadingDirection.RIGHT_TO_LEFT.value
        )
        self.direction_combo.addItem(
            "Esquerda para direita (LTR)", ReadingDirection.LEFT_TO_RIGHT.value
        )
        form.addRow("Direção EPUB", self.direction_combo)

        self.language_input = QLineEdit()
        self.language_input.setObjectName("conversionLanguage")
        self.language_input.setAccessibleName("Idioma obrigatório do EPUB")
        self.language_input.setPlaceholderText("Ex.: pt-BR")
        form.addRow("Idioma EPUB", self.language_input)

        self.max_size_spin = QSpinBox()
        self.max_size_spin.setObjectName("conversionMaxSize")
        self.max_size_spin.setAccessibleName("Limite de tamanho por arquivo em megabytes")
        self.max_size_spin.setRange(0, 20 * 1024)
        self.max_size_spin.setSuffix(" MiB")
        self.max_size_spin.setSpecialValueText("Sem limite")
        self.max_size_spin.setToolTip("Divisão ocorre em fronteiras de página; zero desativa.")
        form.addRow("Tamanho máximo", self.max_size_spin)
        layout.addLayout(form)

        self.validation_label = QLabel("Aguarde o carregamento dos capítulos locais.")
        self.validation_label.setObjectName("conversionValidation")
        self.validation_label.setAccessibleName("Validação da exportação")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        self.status_label = QLabel("Exportação ainda não iniciada.")
        self.status_label.setObjectName("conversionStatus")
        self.status_label.setAccessibleName("Estado da exportação")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.send_to_kindle_button = QPushButton("Continuar para Send to Kindle")
        self.send_to_kindle_button.setObjectName("continueToManualSend")
        self.send_to_kindle_button.setEnabled(False)
        self.send_to_kindle_button.setVisible(False)
        layout.addWidget(self.send_to_kindle_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("conversionProgress")
        self.progress_bar.setAccessibleName("Progresso da exportação local")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        controls = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar capítulos")
        self.refresh_button.setObjectName("refreshExportableChapters")
        self.start_button = QPushButton("Criar arquivos locais")
        self.start_button.setObjectName("startLocalExport")
        self.start_button.setProperty("primaryAction", True)
        self.start_button.setAccessibleName("Criar EPUB ou CBZ local")
        self.cancel_button = QPushButton("Cancelar exportação")
        self.cancel_button.setObjectName("cancelLocalExport")
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.refresh_button)
        controls.addStretch(1)
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)
        layout.addLayout(controls)
        layout.addStretch(1)
        self.content_scroll_area.setWidget(content)
        outer_layout.addWidget(self.content_scroll_area)

        self.choose_folder_button.clicked.connect(self.choose_folder)
        self.refresh_button.clicked.connect(self.refresh_chapters)
        self.start_button.clicked.connect(self.start_export)
        self.cancel_button.clicked.connect(self.cancel_export)
        self.send_to_kindle_button.clicked.connect(self.manual_send_requested.emit)
        self.profile_combo.currentIndexChanged.connect(self._validate_draft)
        self.format_combo.currentIndexChanged.connect(self._validate_draft)
        self.format_combo.currentIndexChanged.connect(self._update_format_controls)
        self.grouping_combo.currentIndexChanged.connect(self._validate_draft)
        self.direction_combo.currentIndexChanged.connect(self._validate_draft)
        self.language_input.textChanged.connect(self._validate_draft)
        self.max_size_spin.valueChanged.connect(self._validate_draft)
        self.output_path.textChanged.connect(self._validate_draft)
        runner.started.connect(self._on_started)
        runner.progress.connect(self._on_progress)
        runner.succeeded.connect(self._on_succeeded)
        runner.failed.connect(self._on_failed)
        runner.cancelled.connect(self._on_cancelled)
        runner.finished.connect(self._on_finished)
        self._validate_draft()

    @property
    def selected_chapter_ids(self) -> tuple[UUID, ...]:
        selected: list[UUID] = []
        for index in range(self.chapter_list.count()):
            item = self.chapter_list.item(index)
            chapter_id = item.data(Qt.ItemDataRole.UserRole)
            if item.checkState() is Qt.CheckState.Checked and isinstance(chapter_id, UUID):
                selected.append(chapter_id)
        return tuple(selected)

    def bind_services(
        self,
        repository: ExportRepositoryPort,
        workflow: CreateExport,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self.refresh_chapters()

    def set_selected_chapters(self, chapter_ids: tuple[UUID, ...]) -> None:
        self._pending_selected_ids = chapter_ids
        self._apply_pending_selection()

    def choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta de saída",
            self.output_path.text(),
        )
        if directory:
            self.output_path.setText(directory)

    def refresh_chapters(self) -> None:
        if self._repository is None or self._load_operation_id is not None:
            return
        repository = self._repository

        def load(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> tuple[ExportableChapter, ...]:
            if cancellation.cancelled:
                return ()
            return repository.list_exportable_chapters()

        operation: BackgroundOperation = load
        self._load_operation_id = self._runner.start(operation)
        self.refresh_button.setEnabled(False)
        self.validation_label.setText("Lendo páginas locais que foram processadas em F006…")

    def start_export(self) -> None:
        if not self._validate_draft() or self._workflow is None:
            return
        try:
            format_value = ExportFormat(self.format_combo.currentData())
            grouping = ExportGrouping(self.grouping_combo.currentData())
            direction = ReadingDirection(self.direction_combo.currentData())
        except (TypeError, ValueError):
            return
        language = self.language_input.text().strip() or None
        profile = DeviceProfile(
            "Páginas processadas F006",
            preferences={"width": 600, "height": 800},
        )
        request = ExportRequest(
            chapter_ids=self.selected_chapter_ids,
            output_directory=Path(self.output_path.text()).expanduser().absolute(),
            profile=profile,
            format=format_value,
            grouping=grouping,
            direction=direction,
            language=language if format_value is ExportFormat.EPUB else None,
            max_size_bytes=(self.max_size_spin.value() * 1024 * 1024)
            if self.max_size_spin.value()
            else None,
        )
        workflow = self._workflow

        def export(cancellation: CancellationToken, report: ProgressReporter) -> ExportResult:
            return workflow.execute(request, cancellation=cancellation, report_progress=report)

        operation: BackgroundOperation = export
        self._export_operation_id = self._runner.start(operation)
        self._set_busy(True)
        self.status_label.setText("Preparando arquivos locais…")
        self.progress_bar.setValue(0)

    def cancel_export(self) -> None:
        if self._export_operation_id is not None:
            if self._runner.cancel(self._export_operation_id):
                self.status_label.setText("Cancelamento solicitado…")
                self.cancel_button.setEnabled(False)

    def _selection_changed(self, _item: QListWidgetItem) -> None:
        self._validate_draft()

    def _validate_draft(self, *_args: object) -> bool:
        selected = self._selected_choices()
        format_value = self.format_combo.currentData()
        grouping = self.grouping_combo.currentData()
        if self._workflow is None or self._repository is None:
            message = "A exportação estará disponível após a inicialização local."
        elif self._load_operation_id is not None:
            message = "Carregando capítulos com todas as páginas processadas…"
        elif not self._chapters:
            message = (
                "Nenhum capítulo está pronto. Importe páginas em F006 e confirme que todas "
                "foram processadas para 600 × 800."
            )
        elif not selected:
            message = "Selecione ao menos um capítulo com páginas processadas."
        elif len({choice.manga_id for choice in selected}) > 1:
            message = "Selecione capítulos de um único mangá por exportação."
        elif self.output_path.text().strip() == "":
            message = "Escolha a pasta local onde os arquivos serão criados."
        elif self.profile_combo.currentData() is None:
            message = "Selecione o perfil correspondente às páginas processadas."
        elif grouping == ExportGrouping.VOLUME.value and any(
            choice.volume is None for choice in selected
        ):
            message = "Agrupamento por volume requer volume conhecido em todos os capítulos."
        elif format_value == ExportFormat.EPUB.value and not _valid_language(
            self.language_input.text()
        ):
            message = "Informe um idioma válido para EPUB, por exemplo pt-BR."
        else:
            message = (
                "Pronto para criar arquivos locais. Arquivos existentes não serão substituídos."
            )
        valid = message.startswith("Pronto para criar")
        self.validation_label.setText(message)
        self.selection_label.setText(
            f"{len(selected)} selecionados · {len(self._chapters)} prontos"
        )
        self.start_button.setEnabled(valid and self._export_operation_id is None)
        return valid

    def _selected_choices(self) -> tuple[ExportableChapter, ...]:
        selected_ids = set(self.selected_chapter_ids)
        return tuple(chapter for chapter in self._chapters if chapter.chapter_id in selected_ids)

    def _apply_pending_selection(self) -> None:
        pending = set(self._pending_selected_ids)
        self.chapter_list.blockSignals(True)
        for index in range(self.chapter_list.count()):
            item = self.chapter_list.item(index)
            chapter_id = item.data(Qt.ItemDataRole.UserRole)
            item.setCheckState(
                Qt.CheckState.Checked
                if chapter_id in pending
                else Qt.CheckState.Unchecked
            )
        self.chapter_list.blockSignals(False)
        self._validate_draft()

    def _set_chapters(self, chapters: tuple[ExportableChapter, ...]) -> None:
        self._chapters = chapters
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        for chapter in chapters:
            item = QListWidgetItem(
                f"{chapter.manga_title}  ·  {chapter.chapter_title}  ·  "
                f"{chapter.page_count} páginas processadas"
            )
            item.setData(Qt.ItemDataRole.UserRole, chapter.chapter_id)
            item.setToolTip(
                "Marque para exportar. O sentido de navegação de CBZ depende do leitor."
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.chapter_list.addItem(item)
        self.chapter_list.blockSignals(False)
        self._apply_pending_selection()
        self.selection_label.setText(
            f"{len(self.selected_chapter_ids)} selecionados · {len(chapters)} prontos"
        )

    def _set_busy(self, busy: bool) -> None:
        for widget in (
            self.chapter_list,
            self.choose_folder_button,
            self.profile_combo,
            self.format_combo,
            self.grouping_combo,
            self.direction_combo,
            self.language_input,
            self.max_size_spin,
            self.refresh_button,
        ):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        if not busy:
            self.start_button.setEnabled(self._validate_draft())

    def _on_started(self, operation_id: str) -> None:
        if operation_id == self._export_operation_id:
            self.status_label.setText("Exportação local em andamento…")

    def _on_progress(
        self,
        operation_id: str,
        completed: int,
        total: object,
        stage: str,
    ) -> None:
        if operation_id != self._export_operation_id:
            return
        if isinstance(total, int) and total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(completed, total))
        else:
            self.progress_bar.setRange(0, 0)
        self.status_label.setText(stage)

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            if isinstance(result, tuple) and all(
                isinstance(item, ExportableChapter) for item in result
            ):
                self._set_chapters(result)
            self.refresh_button.setEnabled(True)
            self._validate_draft()
            return
        if operation_id != self._export_operation_id:
            return
        if not isinstance(result, ExportResult):
            self.status_label.setText("A operação terminou sem um resultado de exportação válido.")
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        has_epub = any(path.suffix.casefold() == ".epub" for path in result.output_paths)
        self.send_to_kindle_button.setVisible(has_epub)
        self.send_to_kindle_button.setEnabled(has_epub)
        file_list = "\n".join(str(path) for path in result.output_paths)
        self.status_label.setText(
            f"Exportação concluída: {len(result.output_paths)} arquivo(s), "
            f"{result.page_count} páginas, {result.total_bytes / 1024 / 1024:.2f} MiB.\n{file_list}"
        )

    def _on_failed(self, operation_id: str, code: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
            self.validation_label.setText(
                "Não foi possível carregar os capítulos locais. Tente atualizar novamente."
            )
            return
        if operation_id != self._export_operation_id:
            return
        message = _ERROR_MESSAGES.get(
            code,
            "Não foi possível concluir a exportação. Os arquivos originais foram preservados.",
        )
        self.status_label.setText(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def _on_cancelled(self, operation_id: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
        elif operation_id == self._export_operation_id:
            self.status_label.setText(
                "Exportação cancelada; os arquivos de origem foram preservados."
            )
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def _on_finished(self, operation_id: str) -> None:
        if operation_id == self._load_operation_id:
            self._load_operation_id = None
            self.refresh_button.setEnabled(True)
        if operation_id == self._export_operation_id:
            self._export_operation_id = None
            self._set_busy(False)

    def _update_format_controls(self, *_args: object) -> None:
        is_epub = self.format_combo.currentData() == ExportFormat.EPUB.value
        self.direction_combo.setEnabled(is_epub and self._export_operation_id is None)
        self.language_input.setEnabled(is_epub and self._export_operation_id is None)


def _valid_language(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", value.strip()) is not None
