"""Fluxo local para conferir e importar imagens originais sem alterar a origem."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.application.images.ports import ImageImportRepositoryPort
from manga_to_kindle.domain.image_processing import (
    ImageImportChapterTarget,
    ImageImportPlan,
    ImageImportTarget,
    ImageProcessingProfile,
    ImageTransformOptions,
    ReadingDirection,
)
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner
from manga_to_kindle.presentation.qt.workers.image_worker import (
    make_image_import_operation,
    make_image_preview_operation,
    make_image_scan_operation,
)

_ERROR_MESSAGES = {
    "IMAGE_SOURCE_REJECTED": (
        "A origem não pôde ser lida com segurança. Confira os arquivos e tente novamente."
    ),
    "IMAGE_LIMIT_EXCEEDED": "A origem excede um limite de tamanho ou quantidade de imagens.",
    "IMAGE_CONTENT_REJECTED": (
        "Uma imagem está corrompida, não é compatível ou não corresponde à extensão."
    ),
    "IMAGE_TARGET_CONFLICT": (
        "O capítulo mudou ou já contém imagens diferentes; nada foi substituído."
    ),
    "IMAGE_IMPORT_CANCELLED": (
        "A importação foi cancelada; os arquivos de origem foram preservados."
    ),
    "IMAGE_STORAGE_FAILED": (
        "Não foi possível concluir a gravação local. A recuperação será tentada ao iniciar."
    ),
}


class ImageImportView(QWidget):
    import_finished = Signal(object)

    def __init__(self, runner: OperationRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._importer: ImportImages | None = None
        self._repository: ImageImportRepositoryPort | None = None
        self._source_path: Path | None = None
        self._plan: ImageImportPlan | None = None
        self._targets: tuple[ImageImportChapterTarget, ...] = ()
        self._target_load_id: str | None = None
        self._scan_id: str | None = None
        self._preview_id: str | None = None
        self._import_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        intro = QLabel(
            "Importe imagens locais ou um CBZ autorizado. A origem permanece intacta e nada é "
            "enviado pela rede."
        )
        intro.setObjectName("imageImportIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        source_actions = QHBoxLayout()
        self.folder_button = QPushButton("Selecionar pasta")
        self.folder_button.setObjectName("selectImageFolder")
        self.folder_button.setAccessibleName("Selecionar uma pasta local de imagens")
        self.cbz_button = QPushButton("Selecionar arquivo CBZ")
        self.cbz_button.setObjectName("selectImageCbz")
        self.cbz_button.setAccessibleName("Selecionar um arquivo CBZ local")
        self.source_label = QLabel("Nenhuma origem selecionada")
        self.source_label.setObjectName("imageImportSource")
        self.source_label.setAccessibleName("Origem local selecionada")
        self.source_label.setWordWrap(True)
        source_actions.addWidget(self.folder_button)
        source_actions.addWidget(self.cbz_button)
        source_actions.addWidget(self.source_label, 1)
        layout.addLayout(source_actions)

        self.scan_button = QPushButton("Verificar e pré-visualizar")
        self.scan_button.setObjectName("scanImageSource")
        self.scan_button.setProperty("primaryAction", True)
        self.scan_button.setEnabled(False)
        layout.addWidget(self.scan_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.status_label = QLabel("Escolha uma pasta ou arquivo CBZ.")
        self.status_label.setObjectName("imageImportStatus")
        self.status_label.setAccessibleName("Estado da importação de imagens")
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("imageImportProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        self.cancel_button = QPushButton("Cancelar operação")
        self.cancel_button.setObjectName("cancelImageOperation")
        self.cancel_button.setAccessibleName("Cancelar leitura ou importação de imagens")
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.status_label)
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.cancel_button)
        layout.addLayout(progress_row)

        preview_row = QHBoxLayout()
        self.image_list = QListWidget()
        self.image_list.setObjectName("imageImportPreviewList")
        self.image_list.setAccessibleName("Imagens reconhecidas na ordem de leitura")
        self.image_list.setMinimumHeight(170)
        self.preview_image = QLabel("A prévia aparecerá aqui")
        self.preview_image.setObjectName("imageImportPreview")
        self.preview_image.setAccessibleName("Prévia do derivado para Kindle")
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setMinimumSize(170, 220)
        self.preview_image.setMaximumWidth(220)
        reorder = QVBoxLayout()
        self.move_up_button = QPushButton("↑")
        self.move_up_button.setAccessibleName("Mover imagem para cima na ordem de leitura")
        self.move_down_button = QPushButton("↓")
        self.move_down_button.setAccessibleName("Mover imagem para baixo na ordem de leitura")
        self.move_up_button.setEnabled(False)
        self.move_down_button.setEnabled(False)
        reorder.addWidget(self.move_up_button)
        reorder.addWidget(self.move_down_button)
        reorder.addStretch(1)
        preview_row.addWidget(self.image_list, 1)
        preview_row.addLayout(reorder)
        preview_row.addWidget(self.preview_image)
        layout.addLayout(preview_row, 1)

        target_form = QFormLayout()
        self.target_combo = QComboBox()
        self.target_combo.setObjectName("imageImportTarget")
        self.target_combo.setAccessibleName("Mangá e capítulo de destino")
        self.target_combo.addItem("Criar novo mangá e capítulo", None)
        self.manga_title_input = QLineEdit()
        self.manga_title_input.setObjectName("newImageMangaTitle")
        self.manga_title_input.setAccessibleName("Título do novo mangá")
        self.chapter_title_input = QLineEdit()
        self.chapter_title_input.setObjectName("newImageChapterTitle")
        self.chapter_title_input.setAccessibleName("Título do novo capítulo")
        self.chapter_number_input = QLineEdit()
        self.chapter_number_input.setObjectName("newImageChapterNumber")
        self.chapter_number_input.setAccessibleName("Número opcional do novo capítulo")
        target_form.addRow("Destino existente ou novo", self.target_combo)
        target_form.addRow("Título do mangá", self.manga_title_input)
        target_form.addRow("Título do capítulo", self.chapter_title_input)
        target_form.addRow("Número do capítulo (opcional)", self.chapter_number_input)
        layout.addLayout(target_form)

        profile_row = QHBoxLayout()
        self.margin_spins: tuple[QSpinBox, ...] = tuple(
            self._make_margin_spin(name)
            for name in ("Esquerda", "Superior", "Direita", "Inferior")
        )
        self.crop_checkbox = QCheckBox("Pré-visualizar recorte de margens")
        self.crop_checkbox.setObjectName("imageCropMargins")
        self.crop_checkbox.setAccessibleName("Aplicar recorte de margens após conferir a prévia")
        self.split_checkbox = QCheckBox("Dividir páginas duplas marcadas")
        self.split_checkbox.setObjectName("imageSplitDoublePages")
        self.split_checkbox.setAccessibleName("Dividir páginas duplas selecionadas")
        self.direction_combo = QComboBox()
        self.direction_combo.setObjectName("imageReadingDirection")
        self.direction_combo.addItem("Direita para esquerda", ReadingDirection.RIGHT_TO_LEFT)
        self.direction_combo.addItem("Esquerda para direita", ReadingDirection.LEFT_TO_RIGHT)
        self.direction_combo.setAccessibleName("Direção de leitura das páginas duplas")
        profile_row.addWidget(QLabel("Margens (px)"))
        for spin in self.margin_spins:
            profile_row.addWidget(spin)
        profile_row.addWidget(self.crop_checkbox)
        profile_row.addWidget(self.split_checkbox)
        profile_row.addWidget(self.direction_combo)
        layout.addLayout(profile_row)

        self.authorization_checkbox = QCheckBox(
            "Confirmo que tenho autorização para manter e processar este conteúdo localmente."
        )
        self.authorization_checkbox.setObjectName("imageImportAuthorization")
        self.authorization_checkbox.setAccessibleName(
            "Confirmo autorização para processar o conteúdo localmente"
        )
        self.import_button = QPushButton("Importar para este dispositivo")
        self.import_button.setObjectName("importLocalImages")
        self.import_button.setProperty("primaryAction", True)
        self.import_button.setEnabled(False)
        final_actions = QHBoxLayout()
        final_actions.addWidget(self.authorization_checkbox)
        final_actions.addStretch(1)
        final_actions.addWidget(self.import_button)
        layout.addLayout(final_actions)

        self.folder_button.clicked.connect(self._choose_folder)
        self.cbz_button.clicked.connect(self._choose_cbz)
        self.scan_button.clicked.connect(self.scan_source)
        self.image_list.currentRowChanged.connect(self._update_selection_controls)
        self.image_list.currentRowChanged.connect(lambda _row: self._request_preview())
        self.image_list.itemChanged.connect(lambda _item: self._request_preview())
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.target_combo.currentIndexChanged.connect(self._update_target_fields)
        self.authorization_checkbox.toggled.connect(self._update_import_enabled)
        self.target_combo.currentIndexChanged.connect(self._update_import_enabled)
        self.manga_title_input.textChanged.connect(self._update_import_enabled)
        self.chapter_title_input.textChanged.connect(self._update_import_enabled)
        self.chapter_number_input.textChanged.connect(self._update_import_enabled)
        self.crop_checkbox.toggled.connect(lambda _checked: self._request_preview())
        self.split_checkbox.toggled.connect(self._split_mode_changed)
        self.direction_combo.currentIndexChanged.connect(lambda _index: self._request_preview())
        for spin in self.margin_spins:
            spin.valueChanged.connect(lambda _value: self._request_preview())
        self.import_button.clicked.connect(self.import_images)
        self.cancel_button.clicked.connect(self.cancel_operation)
        runner.started.connect(self._on_started)
        runner.progress.connect(self._on_progress)
        runner.succeeded.connect(self._on_succeeded)
        runner.failed.connect(self._on_failed)
        runner.cancelled.connect(self._on_cancelled)
        runner.finished.connect(self._on_finished)
        self._update_target_fields()

    def bind_services(
        self,
        importer: ImportImages,
        repository: ImageImportRepositoryPort,
    ) -> None:
        self._importer = importer
        self._repository = repository
        self._reload_targets()

    def _reload_targets(self) -> None:
        if self._repository is None:
            return
        repository = self._repository
        self._target_load_id = self._runner.start(
            lambda cancellation, _report: (
                () if cancellation.cancelled else repository.list_targets()
            )
        )
        self._update_import_enabled()

    def scan_source(self) -> None:
        if self._importer is None or self._source_path is None:
            return
        self._plan = None
        self.image_list.clear()
        self.import_button.setEnabled(False)
        self.preview_image.setText("Verificando imagens…")
        self._scan_id = self._runner.start(
            make_image_scan_operation(self._importer, self._source_path)
        )
        self._set_busy(True)
        self._set_status("Lendo a origem e validando cada imagem…")

    def import_images(self) -> None:
        if self._importer is None or self._plan is None:
            return
        target = self._selected_target()
        if target is None:
            return
        ordered_paths = tuple(
            str(self.image_list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.image_list.count())
        )
        operation = make_image_import_operation(
            self._importer,
            self._plan,
            target,
            ordered_paths=ordered_paths,
            profile=self._profile(),
            options=self._options(),
            confirmed_authorization=self.authorization_checkbox.isChecked(),
        )
        self._import_id = self._runner.start(operation)
        self.import_button.setEnabled(False)
        self._set_busy(True)
        self._set_status("Preparando originais e derivados no perfil local…")

    def cancel_operation(self) -> None:
        operation_id = self._import_id or self._scan_id
        if operation_id is None:
            return
        if self._runner.cancel(operation_id):
            self._set_status("Cancelando com segurança após o item atual…")

    def _choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Selecionar pasta de imagens")
        if directory:
            self._set_source(Path(directory))

    def _choose_cbz(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo CBZ",
            "",
            "Arquivos CBZ (*.cbz)",
        )
        if filename:
            self._set_source(Path(filename))

    def _set_source(self, path: Path) -> None:
        self._source_path = path
        self._plan = None
        self.source_label.setText(_safe_text(path.name))
        self.scan_button.setEnabled(self._importer is not None)
        self.image_list.clear()
        self.import_button.setEnabled(False)
        self._set_status("Origem selecionada. Verifique os itens antes de importar.")

    def _selected_target(self) -> ImageImportTarget | None:
        target = self.target_combo.currentData()
        if isinstance(target, ImageImportChapterTarget):
            return ImageImportTarget(manga_id=target.manga_id, chapter_id=target.chapter_id)
        manga_title = self.manga_title_input.text().strip()
        chapter_title = self.chapter_title_input.text().strip() or None
        chapter_number = self.chapter_number_input.text().strip() or None
        if not manga_title or (chapter_title is None and chapter_number is None):
            return None
        return ImageImportTarget(
            manga_id=uuid4(),
            chapter_id=uuid4(),
            manga_title=manga_title,
            chapter_title=chapter_title,
            chapter_number=chapter_number,
            create_new=True,
        )

    def _profile(self) -> ImageProcessingProfile:
        left, top, right, bottom = (spin.value() for spin in self.margin_spins)
        return ImageProcessingProfile(
            margin_left=left,
            margin_top=top,
            margin_right=right,
            margin_bottom=bottom,
        )

    def _options(self) -> ImageTransformOptions:
        direction = self.direction_combo.currentData()
        reading_direction = (
            direction
            if isinstance(direction, ReadingDirection)
            else ReadingDirection.RIGHT_TO_LEFT
        )
        selected = frozenset(
            str(self.image_list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.image_list.count())
            if self.image_list.item(row).checkState() == Qt.CheckState.Checked
        )
        return ImageTransformOptions(
            crop_margins=self.crop_checkbox.isChecked(),
            split_double_pages=self.split_checkbox.isChecked(),
            reading_direction=reading_direction,
            double_page_paths=selected if self.split_checkbox.isChecked() else frozenset(),
        )

    def _populate_plan(self, plan: ImageImportPlan) -> None:
        self._plan = plan
        self.image_list.blockSignals(True)
        self.image_list.clear()
        for image in plan.images:
            item = QListWidgetItem(
                f"{_safe_text(image.relative_path)}  ·  {image.width}×{image.height}  ·  "
                f"{image.byte_size / 1024:.0f} KiB"
            )
            item.setData(Qt.ItemDataRole.UserRole, image.relative_path)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.image_list.addItem(item)
        self.image_list.blockSignals(False)
        if plan.images:
            self.image_list.setCurrentRow(0)
        self._set_status(
            f"Prévia pronta: {len(plan.images)} imagens válidas; "
            f"{plan.ignored_entries} itens ignorados. Revise a ordem e a prévia do perfil."
        )
        self._update_import_enabled()
        self._request_preview()

    def _request_preview(self) -> None:
        if self._importer is None or self._plan is None:
            return
        item = self.image_list.currentItem()
        if item is None:
            return
        relative_path = str(item.data(Qt.ItemDataRole.UserRole))
        self._preview_id = self._runner.start(
            make_image_preview_operation(
                self._importer,
                self._plan,
                relative_path,
                self._profile(),
                self._options(),
            )
        )
        self.preview_image.setText("Gerando prévia do perfil…")

    def _move_selected(self, offset: int) -> None:
        row = self.image_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.image_list.count():
            return
        item = self.image_list.takeItem(row)
        self.image_list.insertItem(target, item)
        self.image_list.setCurrentRow(target)
        self._update_selection_controls(target)

    def _update_selection_controls(self, row: int) -> None:
        self.move_up_button.setEnabled(row > 0)
        self.move_down_button.setEnabled(0 <= row < self.image_list.count() - 1)
        self._update_import_enabled()

    def _split_mode_changed(self, enabled: bool) -> None:
        self.direction_combo.setEnabled(enabled)
        for row in range(self.image_list.count()):
            item = self.image_list.item(row)
            item.setCheckState(
                Qt.CheckState.Unchecked if not enabled else item.checkState()
            )
        self._request_preview()

    def _update_target_fields(self, _index: int = 0) -> None:
        is_new = self.target_combo.currentData() is None
        for widget in (self.manga_title_input, self.chapter_title_input, self.chapter_number_input):
            widget.setEnabled(is_new)
        self._update_import_enabled()

    def _update_import_enabled(self, *_args: object) -> None:
        ready = (
            self._importer is not None
            and self._plan is not None
            and self.authorization_checkbox.isChecked()
            and self._selected_target() is not None
            and self._import_id is None
        )
        self.import_button.setEnabled(ready)

    def _set_busy(self, busy: bool) -> None:
        self.progress_bar.setVisible(busy)
        can_cancel = self._scan_id is not None or self._import_id is not None
        self.cancel_button.setEnabled(busy and can_cancel)
        if not busy:
            self.progress_bar.setValue(0)
        for widget in (self.folder_button, self.cbz_button, self.scan_button):
            enabled = not busy and (widget is not self.scan_button or self._importer is not None)
            widget.setEnabled(enabled)

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _make_margin_spin(self, label: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 40)
        spin.setValue(0)
        spin.setPrefix(f"{label}: ")
        spin.setAccessibleName(f"Margem {label.lower()} em pixels")
        return spin

    def _on_started(self, operation_id: str) -> None:
        if operation_id in {self._scan_id, self._import_id}:
            self.progress_bar.setValue(0)

    def _on_progress(self, operation_id: str, done: int, total: object, _stage: str) -> None:
        if operation_id not in {self._scan_id, self._import_id}:
            return
        if isinstance(total, int) and total > 0:
            self.progress_bar.setValue(round(done * 100 / total))

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id == self._target_load_id:
            targets = result if isinstance(result, tuple) else ()
            self._targets = tuple(
                item for item in targets if isinstance(item, ImageImportChapterTarget)
            )
            self.target_combo.blockSignals(True)
            while self.target_combo.count() > 1:
                self.target_combo.removeItem(1)
            for target in self._targets:
                label = f"{_safe_text(target.manga_title)} — {_safe_text(target.chapter_title)}"
                if target.has_imported_pages:
                    label += " (imagens locais já importadas)"
                self.target_combo.addItem(label, target)
            self.target_combo.blockSignals(False)
            self._update_import_enabled()
            return
        if operation_id == self._scan_id and isinstance(result, ImageImportPlan):
            self._scan_id = None
            self._set_busy(False)
            self._populate_plan(result)
            return
        if operation_id == self._preview_id:
            previews = result if isinstance(result, tuple) else ()
            if previews and isinstance(previews[0], bytes):
                image = QImage.fromData(previews[0])
                self.preview_image.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        150,
                        200,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            self._preview_id = None
            return
        if operation_id == self._import_id:
            self._import_id = None
            self._set_busy(False)
            imported = getattr(result, "imported_pages", 0)
            processed = getattr(result, "processed_pages", 0)
            duplicates = getattr(result, "duplicate_content_count", 0)
            if getattr(result, "idempotent", False):
                message = "Esta importação idêntica já existe; nenhuma página foi duplicada."
            else:
                message = (
                    f"Importação local concluída: {imported} originais e "
                    f"{processed} derivados."
                )
            if duplicates:
                message += f" Conteúdos repetidos em posições diferentes: {duplicates}."
            self._set_status(message)
            self._update_import_enabled()
            self._reload_targets()
            self.import_finished.emit(result)

    def _on_failed(self, operation_id: str, error_code: str) -> None:
        if operation_id == self._scan_id:
            self._scan_id = None
            self._set_busy(False)
        elif operation_id == self._import_id:
            self._import_id = None
            self._set_busy(False)
        elif operation_id == self._preview_id:
            self._preview_id = None
        else:
            return
        self._set_status(
            _ERROR_MESSAGES.get(error_code, "A operação local não pôde ser concluída.")
        )
        self._update_import_enabled()

    def _on_cancelled(self, operation_id: str) -> None:
        if operation_id == self._scan_id:
            self._scan_id = None
            self._set_busy(False)
        elif operation_id == self._import_id:
            self._import_id = None
            self._set_busy(False)
            self._set_status("Importação cancelada; a origem foi preservada.")
        elif operation_id == self._preview_id:
            self._preview_id = None
        self._update_import_enabled()

    def _on_finished(self, operation_id: str) -> None:
        if operation_id == self._target_load_id:
            self._target_load_id = None


def _safe_text(value: str) -> str:
    return "".join(
        "�" if unicodedata.category(character).startswith("C") else character
        for character in value
    )
