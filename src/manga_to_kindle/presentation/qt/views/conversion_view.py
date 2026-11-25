"""Prévia de conversão sem escrever arquivo nem declarar compatibilidade real."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.presentation.qt.view_models import (
    DemoResult,
    resolve_demo_outcome,
)
from manga_to_kindle.presentation.qt.views.components import DemoJobPanel
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)
from manga_to_kindle.presentation.qt.workers.demo import make_demo_operation


class OutputDirectoryUnavailableError(RuntimeError):
    code = "OUTPUT_DIRECTORY_UNAVAILABLE"


class ConversionView(QWidget):
    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_chapter_ids: tuple[UUID, ...] = ()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        intro = QLabel(
            "Escolha capítulos e opções de demonstração. Nenhum arquivo será criado."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        form = QFormLayout()
        self.selection_label = QLabel("Nenhum capítulo selecionado")
        self.selection_label.setObjectName("conversionSelection")
        self.selection_label.setAccessibleName("Capítulos selecionados para demonstração")
        form.addRow("Seleção", self.selection_label)

        output_row = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setObjectName("conversionOutputPath")
        self.output_path.setReadOnly(True)
        self.output_path.setPlaceholderText("Selecione uma pasta de saída")
        self.output_path.setAccessibleName("Pasta de saída escolhida")
        self.choose_folder_button = QPushButton("Escolher pasta…")
        self.choose_folder_button.setObjectName("chooseOutputFolder")
        self.choose_folder_button.setAccessibleName("Escolher pasta de saída")
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(self.choose_folder_button)
        form.addRow("Pasta de saída", output_row)

        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("conversionProfile")
        self.profile_combo.setAccessibleName("Perfil Kindle de demonstração")
        self.profile_combo.addItem("Selecione um perfil", None)
        self.profile_combo.addItem("Kindle básico — simulado", "kindle-basic-demo")
        self.profile_combo.addItem("Kindle Paperwhite — simulado", "kindle-paperwhite-demo")
        form.addRow("Perfil Kindle", self.profile_combo)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("conversionFormat")
        self.format_combo.setAccessibleName("Formato de demonstração")
        self.format_combo.addItem("Selecione um formato", None)
        self.format_combo.addItem("EPUB — simulado", "epub-demo")
        self.format_combo.addItem("CBZ — simulado", "cbz-demo")
        self.format_combo.addItem("AZW3 — simulado", "azw3-demo")
        form.addRow("Formato", self.format_combo)

        self.validation_label = QLabel("Selecione capítulos e uma pasta para continuar.")
        self.validation_label.setObjectName("conversionValidation")
        self.validation_label.setAccessibleName("Validação da demonstração de conversão")
        self.validation_label.setWordWrap(True)
        self.job_panel = DemoJobPanel(
            runner,
            action_text="Iniciar conversão simulada",
            summary="Prévia simulada concluída.",
        )
        self.job_panel.set_can_start(False)
        self.job_panel.start_button.clicked.disconnect()
        self.job_panel.start_button.clicked.connect(self.start_conversion)
        self.choose_folder_button.clicked.connect(self.choose_folder)
        self.profile_combo.currentIndexChanged.connect(self._validate_draft)
        self.format_combo.currentIndexChanged.connect(self._validate_draft)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.validation_label)
        layout.addWidget(self.job_panel)
        layout.addStretch(1)

    @property
    def selected_chapter_ids(self) -> tuple[UUID, ...]:
        return self._selected_chapter_ids

    def set_selected_chapters(self, chapter_ids: tuple[UUID, ...]) -> None:
        self._selected_chapter_ids = chapter_ids
        count = len(chapter_ids)
        self.selection_label.setText(
            f"{count} capítulo selecionado" if count == 1 else f"{count} capítulos selecionados"
        )
        self._validate_draft()

    def choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta de saída",
            self.output_path.text(),
        )
        if directory:
            self.output_path.setText(directory)
            self._validate_draft()

    def start_conversion(self) -> None:
        if not self._validate_draft():
            return
        output_directory = Path(self.output_path.text())
        outcome = resolve_demo_outcome(self.job_panel.outcome_combo.currentData())
        demo = make_demo_operation(outcome, summary="Prévia simulada concluída.")

        def validate_and_run(
            cancellation: CancellationToken,
            report: ProgressReporter,
        ) -> DemoResult:
            if cancellation.cancelled:
                return DemoResult(simulated=True, summary="Prévia cancelada.")
            if not output_directory.is_dir():
                raise OutputDirectoryUnavailableError("Output folder is unavailable.")
            result = demo(cancellation, report)
            if isinstance(result, DemoResult):
                return result
            return DemoResult(simulated=True, summary="Prévia simulada concluída.")

        operation: BackgroundOperation = validate_and_run
        self.job_panel.start_operation(operation)

    def _validate_draft(self) -> bool:
        if not self._selected_chapter_ids:
            message = "Selecione ao menos um capítulo."
        elif not self.output_path.text().strip():
            message = "Escolha uma pasta de saída."
        elif self.profile_combo.currentData() is None:
            message = "Escolha um perfil Kindle de demonstração."
        elif self.format_combo.currentData() is None:
            message = "Escolha um formato de demonstração."
        else:
            message = "Opções válidas para a demonstração; nenhum arquivo será criado."
        is_valid = message.startswith("Opções válidas")
        self.validation_label.setText(message)
        self.job_panel.set_can_start(is_valid)
        return is_valid

