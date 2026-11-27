"""Local device profiles, reading defaults, resources, and theme settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.settings.cache import (
    CacheCleanupError,
    CacheCleanupPreview,
    CacheCleanupResult,
    ClearRegenerableCache,
    PreviewCacheCleanup,
)
from manga_to_kindle.application.settings.device_profiles import (
    DeviceProfileError,
    ListDeviceProfiles,
    RemoveDeviceProfile,
    SaveDeviceProfile,
)
from manga_to_kindle.application.settings.preferences import (
    GetApplicationPreferences,
    PreferenceError,
    ResetPreferences,
    SaveApplicationPreferences,
)
from manga_to_kindle.application.ui.theme_mode import ThemeMode
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.settings import (
    BASIC_10_PROFILE_ID,
    MIB,
    ApplicationPreferences,
    DeviceProfileSettings,
)
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)


class SettingsView(QWidget):
    theme_changed = Signal(str)
    preferences_ready = Signal(object, object)

    def __init__(
        self,
        runner: OperationRunner | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._profiles: tuple[DeviceProfileSettings, ...] = ()
        self._preferences: ApplicationPreferences | None = None
        self._get_preferences: GetApplicationPreferences | None = None
        self._list_profiles: ListDeviceProfiles | None = None
        self._save_profile: SaveDeviceProfile | None = None
        self._remove_profile: RemoveDeviceProfile | None = None
        self._save_preferences: SaveApplicationPreferences | None = None
        self._reset_preferences: ResetPreferences | None = None
        self._preview_cache: PreviewCacheCleanup | None = None
        self._clear_cache: ClearRegenerableCache | None = None
        self._operation_kinds: dict[str, str] = {}
        self._cache_preview: CacheCleanupPreview | None = None
        self._loading_profile = False

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(14)
        self.title = QLabel("Configurações")
        self.title.setObjectName("settingsTitle")
        self.title.setStyleSheet("font-size: 17px; font-weight: 650;")
        self.description = QLabel(
            "Perfis e preferências valem para novos trabalhos. Arquivos existentes não são movidos."
        )
        self.description.setObjectName("settingsDescription")
        self.description.setWordWrap(True)
        outer_layout.addWidget(self.title)
        outer_layout.addWidget(self.description)

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("settingsTabs")
        outer_layout.addWidget(self.tabs, 1)
        self._build_profiles_tab()
        self._build_processing_tab()
        self._build_resources_tab()
        self._build_appearance_tab()

        self.status_label = QLabel("As preferências serão carregadas após a inicialização local.")
        self.status_label.setObjectName("settingsStatus")
        self.status_label.setAccessibleName("Estado das configurações")
        self.status_label.setWordWrap(True)
        outer_layout.addWidget(self.status_label)

        if self._runner is not None:
            self._runner.succeeded.connect(self._on_succeeded)
            self._runner.failed.connect(self._on_failed)
            self._runner.finished.connect(self._on_finished)

    def bind_services(
        self,
        get_preferences: GetApplicationPreferences,
        list_profiles: ListDeviceProfiles,
        save_profile: SaveDeviceProfile,
        remove_profile: RemoveDeviceProfile,
        save_preferences: SaveApplicationPreferences,
        reset_preferences: ResetPreferences,
        preview_cache: PreviewCacheCleanup,
        clear_cache: ClearRegenerableCache,
    ) -> None:
        self._get_preferences = get_preferences
        self._list_profiles = list_profiles
        self._save_profile = save_profile
        self._remove_profile = remove_profile
        self._save_preferences = save_preferences
        self._reset_preferences = reset_preferences
        self._preview_cache = preview_cache
        self._clear_cache = clear_cache
        self._run("load", self._load_settings)

    def set_theme(self, theme: ThemeMode, *, emit: bool = False) -> None:
        button = self.dark_button if theme == "dark" else self.light_button
        if not emit:
            self.light_button.blockSignals(True)
            self.dark_button.blockSignals(True)
        button.setChecked(True)
        if not emit:
            self.light_button.blockSignals(False)
            self.dark_button.blockSignals(False)

    def _build_profiles_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("deviceProfileSelect")
        self.profile_combo.setAccessibleName("Perfil de dispositivo ativo")
        self.profile_combo.currentIndexChanged.connect(self._profile_selected)
        layout.addWidget(self.profile_combo)

        self.profile_form = QFormLayout()
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setObjectName("deviceProfileName")
        self.profile_name_input.setAccessibleName("Nome do perfil de dispositivo")
        self.profile_model_input = QLineEdit()
        self.profile_model_input.setObjectName("deviceProfileModel")
        self.width_spin = _spin(1, 10_000, "Largura em pixels")
        self.height_spin = _spin(1, 10_000, "Altura em pixels")
        self.ppi_spin = _spin(0, 1200, "Densidade em pixels por polegada")
        self.ppi_spin.setSpecialValueText("Não informado")
        self.grayscale_label = QLabel("Escala de cinza — saída atual em tons de cinza")
        self.grayscale_label.setObjectName("profileGrayscaleInfo")
        self.direction_combo = QComboBox()
        self.direction_combo.setObjectName("profileReadingDirection")
        self.direction_combo.addItem("Direita para esquerda (RTL)", ReadingDirection.RIGHT_TO_LEFT)
        self.direction_combo.addItem("Esquerda para direita (LTR)", ReadingDirection.LEFT_TO_RIGHT)
        self.margin_spins = tuple(
            _spin(0, 40, f"Margem {label.lower()} em pixels")
            for label in ("esquerda", "superior", "direita", "inferior")
        )
        margin_row = QHBoxLayout()
        for spin in self.margin_spins:
            margin_row.addWidget(spin)
        self.crop_checkbox = QCheckBox(
            "Usar recorte como padrão (sempre exige prévia e confirmação)"
        )
        self.crop_checkbox.setObjectName("profileCropMargins")
        self.quality_spin = _spin(1, 100, "Qualidade com perda entre 1 e 100")
        self.quality_spin.setObjectName("profileQuality")
        self.quality_note = QLabel(
            "O pipeline atual grava PNG sem perda; qualidade não altera os arquivos atuais."
        )
        self.quality_note.setObjectName("qualityNotApplicable")
        self.quality_note.setWordWrap(True)
        self.profile_form.addRow("Nome", self.profile_name_input)
        self.profile_form.addRow("Modelo", self.profile_model_input)
        self.profile_form.addRow("Largura", self.width_spin)
        self.profile_form.addRow("Altura", self.height_spin)
        self.profile_form.addRow("Densidade", self.ppi_spin)
        self.profile_form.addRow("Tela", self.grayscale_label)
        self.profile_form.addRow("Direção padrão", self.direction_combo)
        self.profile_form.addRow("Margens (px)", margin_row)
        self.profile_form.addRow("Recorte", self.crop_checkbox)
        quality_row = QVBoxLayout()
        quality_row.addWidget(self.quality_spin)
        quality_row.addWidget(self.quality_note)
        self.profile_form.addRow("Qualidade", quality_row)
        layout.addLayout(self.profile_form)

        actions = QHBoxLayout()
        self.duplicate_profile_button = QPushButton("Duplicar perfil…")
        self.duplicate_profile_button.setObjectName("duplicateDeviceProfile")
        self.save_profile_button = QPushButton("Aplicar perfil e salvar configurações")
        self.save_profile_button.setObjectName("saveDeviceProfile")
        self.remove_profile_button = QPushButton("Remover perfil")
        self.remove_profile_button.setObjectName("removeDeviceProfile")
        actions.addWidget(self.duplicate_profile_button)
        actions.addWidget(self.save_profile_button)
        actions.addWidget(self.remove_profile_button)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.duplicate_profile_button.clicked.connect(self._duplicate_profile)
        self.save_profile_button.clicked.connect(self._save_all)
        self.remove_profile_button.clicked.connect(self._confirm_remove_profile)
        self.tabs.addTab(page, "Perfil de dispositivo")

    def _build_processing_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        note = QLabel(
            "As alterações são aplicadas somente a novas importações e exports. "
            "Originais e trabalhos existentes permanecem intactos."
        )
        note.setObjectName("readingSettingsNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(
            QLabel(
                "O perfil Básico 8ª/10ª usa quadro 600 × 800, 167 ppi e "
                "16 níveis de cinza."
            )
        )
        layout.addWidget(
            QLabel("O Paperwhite 10ª usa quadro 1072 × 1448, 300 ppi e 16 níveis de cinza.")
        )
        layout.addWidget(
            QLabel(
                "O perfil define resolução de saída; não detecta Kindle nem garante "
                "compatibilidade física."
            )
        )
        layout.addStretch(1)
        self.tabs.addTab(page, "Leitura e processamento")

    def _build_resources_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.concurrency_spin = _spin(1, 2, "Máximo de downloads simultâneos")
        form.addRow("Concorrência de downloads", self.concurrency_spin)
        self.download_path, self.download_path_button = _directory_row("Pasta de downloads padrão")
        self.export_path, self.export_path_button = _directory_row("Pasta de exports padrão")
        self.cache_path, self.cache_path_button = _directory_row("Pasta de cache regenerável")
        form.addRow(
            "Downloads", self.download_path_row(self.download_path, self.download_path_button)
        )
        form.addRow(
            "Exports", self.download_path_row(self.export_path, self.export_path_button)
        )
        form.addRow("Cache", self.download_path_row(self.cache_path, self.cache_path_button))
        self.cache_limit_spin = _spin(100, 20 * 1024, "Limite de cache em MiB")
        self.cache_limit_spin.setSuffix(" MiB")
        self.cache_retention_spin = _spin(1, 365, "Dias de retenção do cache")
        self.cache_retention_spin.setSuffix(" dias")
        form.addRow("Limite de cache", self.cache_limit_spin)
        form.addRow("Retenção", self.cache_retention_spin)
        layout.addLayout(form)
        self.clear_cache_button = QPushButton("Revisar e limpar cache…")
        self.clear_cache_button.setObjectName("clearRegenerableCache")
        self.clear_cache_button.clicked.connect(self._preview_cache_cleanup)
        layout.addWidget(self.clear_cache_button)
        note = QLabel(
            "A limpeza usa somente itens íntegros registrados no manifesto de cache. "
            "Originais, páginas processadas, downloads, exports e arquivos desconhecidos "
            "são preservados."
        )
        note.setObjectName("cacheSafetyNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        for line_edit, button in (
            (self.download_path, self.download_path_button),
            (self.export_path, self.export_path_button),
            (self.cache_path, self.cache_path_button),
        ):
            button.clicked.connect(
                lambda _checked=False, target=line_edit: self._choose_directory(target)
            )
        self.tabs.addTab(page, "Pastas e recursos")

    def _build_appearance_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Aparência")
        description = QLabel(
            "O tema claro é o padrão. A escolha é aplicada à janela e salva localmente."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        self.light_button = QRadioButton("Tema claro")
        self.light_button.setObjectName("themeLight")
        self.light_button.setAccessibleName("Usar tema claro")
        self.dark_button = QRadioButton("Tema escuro")
        self.dark_button.setObjectName("themeDark")
        self.dark_button.setAccessibleName("Usar tema escuro")
        group = QButtonGroup(self)
        group.addButton(self.light_button)
        group.addButton(self.dark_button)
        self.light_button.toggled.connect(
            lambda checked: self.theme_changed.emit("light") if checked else None
        )
        self.dark_button.toggled.connect(
            lambda checked: self.theme_changed.emit("dark") if checked else None
        )
        self.restore_button = QPushButton("Restaurar padrões…")
        self.restore_button.setObjectName("restoreDefaultSettings")
        self.restore_button.clicked.connect(self._confirm_restore)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.light_button)
        layout.addWidget(self.dark_button)
        layout.addWidget(self.restore_button)
        layout.addStretch(1)
        self.tabs.addTab(page, "Aparência e restauração")
        self.set_theme("light", emit=False)

    @staticmethod
    def download_path_row(path_input: QLineEdit, button: QPushButton) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(path_input, 1)
        layout.addWidget(button)
        return row

    def _load_settings(self) -> tuple[ApplicationPreferences, tuple[DeviceProfileSettings, ...]]:
        if self._get_preferences is None or self._list_profiles is None:
            raise PreferenceError("O serviço de configurações não está disponível.")
        return self._get_preferences.execute(), self._list_profiles.execute()

    def _start_operation(self, kind: str, operation: BackgroundOperation) -> None:
        if self._runner is None:
            self.status_label.setText("O serviço de configurações não está disponível.")
            return
        operation_id = self._runner.start(operation)
        self._operation_kinds[operation_id] = kind
        self.status_label.setText("Salvando ou consultando configurações locais…")
        self._set_busy(True)

    def _run(self, kind: str, callback: Callable[[], object]) -> None:
        def operation(
            cancellation: CancellationToken,
            _report: ProgressReporter,
        ) -> object:
            if cancellation.cancelled:
                return None
            return callback()

        background: BackgroundOperation = operation
        self._start_operation(kind, background)

    def _profile_selected(self, _index: int) -> None:
        if self._loading_profile:
            return
        profile_id = self.profile_combo.currentData()
        profile = next((item for item in self._profiles if item.id == profile_id), None)
        if profile is not None:
            self._show_profile(profile)

    def _show_profile(self, profile: DeviceProfileSettings) -> None:
        self._loading_profile = True
        self.profile_name_input.setText(profile.name)
        self.profile_model_input.setText(profile.model)
        self.width_spin.setValue(profile.width)
        self.height_spin.setValue(profile.height)
        self.ppi_spin.setValue(profile.ppi or 0)
        direction_index = self.direction_combo.findData(profile.direction)
        self.direction_combo.setCurrentIndex(max(0, direction_index))
        for spin, value in zip(
            self.margin_spins,
            (profile.margin_left, profile.margin_top, profile.margin_right, profile.margin_bottom),
            strict=True,
        ):
            spin.setValue(value)
        self.crop_checkbox.setChecked(profile.crop_margins)
        self.quality_spin.setValue(profile.quality)
        self._loading_profile = False
        self.profile_name_input.setEnabled(not profile.built_in)
        self.profile_model_input.setEnabled(not profile.built_in)
        self.width_spin.setEnabled(not profile.built_in)
        self.height_spin.setEnabled(not profile.built_in)
        self.ppi_spin.setEnabled(not profile.built_in)
        self.direction_combo.setEnabled(not profile.built_in)
        for spin in self.margin_spins:
            spin.setEnabled(not profile.built_in)
        self.crop_checkbox.setEnabled(not profile.built_in)
        self.quality_spin.setEnabled(not profile.built_in)
        self.save_profile_button.setEnabled(True)
        self.remove_profile_button.setEnabled(
            not profile.built_in
            and (self._preferences is None or profile.id != self._preferences.selected_profile_id)
        )

    def _duplicate_profile(self) -> None:
        save_profile = self._save_profile
        if save_profile is None:
            return
        source_id = self.profile_combo.currentData()
        if not isinstance(source_id, UUID):
            return
        from PySide6.QtWidgets import QInputDialog

        name, accepted = QInputDialog.getText(self, "Duplicar perfil", "Nome do novo perfil")
        if not accepted or not name.strip():
            return
        self._run(
            "duplicate",
            lambda: save_profile.duplicate(source_id, name),
        )

    def _save_all(self) -> None:
        save_profile = self._save_profile
        save_preferences = self._save_preferences
        list_profiles = self._list_profiles
        if (
            self._preferences is None
            or save_profile is None
            or save_preferences is None
            or list_profiles is None
        ):
            return
        profile_id = self.profile_combo.currentData()
        profile = next((item for item in self._profiles if item.id == profile_id), None)
        if profile is None:
            return
        try:
            preferences = self._preferences_from_controls(profile.id)
            profile_to_save = None if profile.built_in else self._profile_from_controls(profile)
        except DomainValidationError as error:
            self.status_label.setText(str(error))
            return

        def save() -> tuple[ApplicationPreferences, tuple[DeviceProfileSettings, ...]]:
            if profile_to_save is not None:
                save_profile.execute(profile_to_save)
            save_preferences.execute(preferences)
            return preferences, list_profiles.execute()

        self._run("save", save)

    def _profile_from_controls(self, current: DeviceProfileSettings) -> DeviceProfileSettings:
        try:
            direction = ReadingDirection(str(self.direction_combo.currentData()))
        except ValueError:
            direction = ReadingDirection.RIGHT_TO_LEFT
        left, top, right, bottom = (spin.value() for spin in self.margin_spins)
        return DeviceProfileSettings(
            id=current.id,
            name=self.profile_name_input.text(),
            model=self.profile_model_input.text(),
            generation=current.generation,
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            ppi=self.ppi_spin.value() or None,
            grayscale_levels=16,
            grayscale=True,
            direction=direction,
            margin_left=left,
            margin_top=top,
            margin_right=right,
            margin_bottom=bottom,
            crop_margins=self.crop_checkbox.isChecked(),
            quality=self.quality_spin.value(),
        )

    def _preferences_from_controls(self, selected_profile_id: UUID) -> ApplicationPreferences:
        return ApplicationPreferences(
            selected_profile_id=selected_profile_id,
            download_concurrency=self.concurrency_spin.value(),
            download_directory=Path(self.download_path.text()),
            export_directory=Path(self.export_path.text()),
            cache_directory=Path(self.cache_path.text()),
            cache_limit_bytes=self.cache_limit_spin.value() * MIB,
            cache_retention_days=self.cache_retention_spin.value(),
        )

    def _choose_directory(self, target: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Escolher pasta padrão", target.text())
        if selected:
            target.setText(selected)

    def _confirm_remove_profile(self) -> None:
        remove_profile = self._remove_profile
        profile_id = self.profile_combo.currentData()
        profile = next((item for item in self._profiles if item.id == profile_id), None)
        if profile is None or profile.built_in or remove_profile is None:
            return
        choice = QMessageBox.question(
            self,
            "Remover perfil personalizado",
            f"Remover o perfil ‘{profile.name}’? Nenhum arquivo ou export será removido.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice is not QMessageBox.StandardButton.Yes:
            return
        self._run("remove", lambda: remove_profile.execute(profile.id))

    def _confirm_restore(self) -> None:
        reset_preferences = self._reset_preferences
        if reset_preferences is None:
            return
        choice = QMessageBox.question(
            self,
            "Restaurar preferências padrão",
            "As preferências de recursos voltarão ao padrão, inclusive perfil Básico 10ª, "
            "concorrência 2, pastas locais, cache 1 GiB/30 dias e tema claro. "
            "Biblioteca, arquivos, exports, perfis personalizados e credenciais serão preservados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice is not QMessageBox.StandardButton.Yes:
            return
        self._run("reset", lambda: reset_preferences.execute(confirmed=True))

    def _preview_cache_cleanup(self) -> None:
        preview_cache = self._preview_cache
        if preview_cache is None or self._preferences is None:
            return
        preferences = self._preferences
        cache_directory = preferences.cache_directory
        if cache_directory is None:
            return
        self._run(
            "cache-preview",
            lambda: preview_cache.execute(
                cache_directory,
                limit_bytes=preferences.cache_limit_bytes,
                retention_days=preferences.cache_retention_days,
                clear_all=False,
            ),
        )

    def _confirm_cache_cleanup(self, preview: CacheCleanupPreview) -> None:
        self._cache_preview = preview
        if preview.file_count == 0:
            self.status_label.setText("O manifesto não contém arquivos de cache para limpar.")
            return
        mebibytes = preview.total_bytes / MIB
        choice = QMessageBox.question(
            self,
            "Confirmar limpeza do cache",
            f"Remover {preview.file_count} arquivo(s) registrados no cache, "
            f"totalizando {mebibytes:.1f} MiB? Arquivos sem vínculo serão preservados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        clear_cache = self._clear_cache
        if choice is not QMessageBox.StandardButton.Yes or clear_cache is None:
            self.status_label.setText(
                "A limpeza do cache foi cancelada; nenhum arquivo foi alterado."
            )
            return
        self._run("cache-clear", lambda: clear_cache.execute(preview, confirmed=True))

    def _confirm_loaded_cache_cleanup(self, result: CacheCleanupResult) -> None:
        self.status_label.setText(
            f"Cache: {result.removed_count} arquivo(s) removido(s), "
            f"{result.removed_bytes / MIB:.1f} MiB liberados; "
            f"{result.preserved_count} item(ns) alterado(s) foram preservados."
        )

    def _apply_preferences(self, preferences: ApplicationPreferences) -> None:
        self._preferences = preferences
        self.concurrency_spin.setValue(preferences.download_concurrency)
        self.download_path.setText(str(preferences.download_directory or ""))
        self.export_path.setText(str(preferences.export_directory or ""))
        self.cache_path.setText(str(preferences.cache_directory or ""))
        self.cache_limit_spin.setValue(preferences.cache_limit_bytes // MIB)
        self.cache_retention_spin.setValue(preferences.cache_retention_days)

    def _apply_profiles(self, profiles: tuple[DeviceProfileSettings, ...]) -> None:
        if not profiles:
            self.status_label.setText("Nenhum perfil de dispositivo está disponível.")
            return
        self._profiles = profiles
        selected_id = (
            self._preferences.selected_profile_id
            if self._preferences is not None
            else profiles[1].id if len(profiles) > 1 else profiles[0].id
        )
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in profiles:
            self.profile_combo.addItem(
                f"{profile.name} — {profile.width} × {profile.height} px",
                profile.id,
            )
        index = self.profile_combo.findData(selected_id)
        if index < 0:
            index = next(
                (i for i, profile in enumerate(profiles) if profile.id == BASIC_10_PROFILE_ID),
                0,
            )
            if self._preferences is not None:
                self._preferences = replace(
                    self._preferences,
                    selected_profile_id=profiles[index].id,
                )
        self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)
        if self._preferences is not None:
            self._show_profile(profiles[index])
            self.remove_profile_button.setEnabled(
                not profiles[index].built_in
                and profiles[index].id != self._preferences.selected_profile_id
            )

    def _set_busy(self, busy: bool) -> None:
        for widget in (
            self.profile_combo,
            self.duplicate_profile_button,
            self.save_profile_button,
            self.remove_profile_button,
            self.concurrency_spin,
            self.download_path_button,
            self.export_path_button,
            self.cache_path_button,
            self.cache_limit_spin,
            self.cache_retention_spin,
            self.clear_cache_button,
            self.restore_button,
        ):
            widget.setEnabled(not busy)

    def _on_succeeded(self, operation_id: str, result: object) -> None:
        kind = self._operation_kinds.get(operation_id)
        if kind == "load" and isinstance(result, tuple) and len(result) == 2:
            preferences, profiles = result
            if isinstance(preferences, ApplicationPreferences):
                self._apply_preferences(preferences)
                self._apply_profiles(profiles)
                self.preferences_ready.emit(self._preferences or preferences, profiles)
                self.status_label.setText("Preferências e perfis locais carregados.")
        elif kind == "save" and isinstance(result, tuple) and len(result) == 2:
            preferences, profiles = result
            self._apply_preferences(preferences)
            self._apply_profiles(profiles)
            self.preferences_ready.emit(self._preferences or preferences, profiles)
            self.status_label.setText("Preferências e perfil salvos para novos trabalhos.")
        elif kind == "duplicate" and isinstance(result, DeviceProfileSettings):
            self._profiles = (*self._profiles, result)
            self._preferences = self._preferences_from_controls(result.id)
            self._apply_profiles(self._profiles)
            self.status_label.setText("Perfil personalizado criado; ajuste e salve os valores.")
        elif kind == "remove" and result is True:
            self._run("reload", self._load_settings)
            self.status_label.setText(
                "Perfil removido. Biblioteca, exports e arquivos não foram alterados."
            )
        elif kind == "reset" and isinstance(result, ApplicationPreferences):
            self.set_theme("light", emit=True)
            self._apply_preferences(result)
            self._run("reload", self._load_settings)
            self.status_label.setText(
                "Preferências padrão restauradas; perfis e conteúdo foram preservados."
            )
        elif kind == "cache-preview" and isinstance(result, CacheCleanupPreview):
            self._confirm_cache_cleanup(result)
        elif kind == "cache-clear" and isinstance(result, CacheCleanupResult):
            self._confirm_loaded_cache_cleanup(result)

    def _on_failed(self, operation_id: str, code: str) -> None:
        if operation_id not in self._operation_kinds:
            return
        messages = {
            DeviceProfileError.code: "O perfil é inválido, está em uso ou não pode ser alterado.",
            PreferenceError.code: "Revise as pastas e os limites antes de salvar.",
            CacheCleanupError.code: (
                "Um item de cache mudou ou não pôde ser validado; ele foi preservado."
            ),
        }
        self.status_label.setText(
            messages.get(code, "Não foi possível salvar as configurações locais.")
        )

    def _on_finished(self, operation_id: str) -> None:
        if self._operation_kinds.pop(operation_id, None) is not None:
            self._set_busy(bool(self._operation_kinds))


def _spin(minimum: int, maximum: int, accessible_name: str) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setAccessibleName(accessible_name)
    return spin


def _directory_row(title: str) -> tuple[QLineEdit, QPushButton]:
    path_input = QLineEdit()
    path_input.setReadOnly(True)
    path_input.setAccessibleName(title)
    button = QPushButton("Escolher…")
    button.setAccessibleName(f"{title}: escolher pasta existente")
    return path_input, button
