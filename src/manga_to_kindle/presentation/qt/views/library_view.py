"""Biblioteca local com consultas em worker e escopo explícito de exclusão."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.domain.library import (
    ActivityKind,
    AvailabilityState,
    LibraryActivity,
    LibraryAsset,
    LibraryAssetCategory,
    LibraryAssetState,
    LibraryDeletionPreview,
    LibraryEntry,
    LibraryPage,
    LibraryPreferences,
    LibraryQuery,
    LibrarySort,
)
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.presentation.qt.views.components import EmptyState
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
)


class LibraryDeleteDialog(QDialog):
    """Mostra os registros e cada arquivo antes da confirmação final."""

    def __init__(self, preview: LibraryDeletionPreview, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle("Revisar remoção da biblioteca")
        self.setModal(True)
        self.resize(680, 560)
        layout = QVBoxLayout(self)
        heading = QLabel(f"Remover {preview.manga_title} da biblioteca?")
        heading.setStyleSheet("font-size: 17px; font-weight: 650;")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        count_lines = [f"• {label}: {count}" for label, count in preview.record_counts]
        self.record_summary = QLabel("\n".join(count_lines))
        self.record_summary.setObjectName("libraryDeleteRecordSummary")
        self.record_summary.setWordWrap(True)
        layout.addWidget(self.record_summary)
        note = QLabel(
            "O histórico de importação e exportação permanece. Trabalhos e progresso de "
            "download ligados a este mangá são removidos com os registros. Os arquivos "
            "ficam sem vínculo se você não os selecionar abaixo. "
            "Pastas de origem nunca são removidas."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.asset_scroll = QScrollArea()
        self.asset_scroll.setWidgetResizable(True)
        self.asset_list = QWidget()
        self.asset_layout = QVBoxLayout(self.asset_list)
        self.asset_layout.setContentsMargins(4, 4, 4, 4)
        self.asset_layout.setSpacing(7)
        self.asset_checks: dict[str, QCheckBox] = {}
        for asset in preview.assets:
            checkbox = QCheckBox(self._asset_description(asset))
            checkbox.setAccessibleName(f"Excluir arquivo {asset.path.name}")
            checkbox.setObjectName(f"deleteAsset_{asset.id.replace(':', '_')}")
            checkbox.setToolTip(str(asset.path))
            can_delete = (
                asset.state is LibraryAssetState.AVAILABLE
                and not asset.shared
                and asset.sha256 is not None
                and (asset.managed or asset.category is LibraryAssetCategory.EXPORT)
            )
            checkbox.setEnabled(can_delete)
            if not can_delete:
                reason = (
                    "Arquivo ausente ou alterado; será preservado."
                    if asset.state is not LibraryAssetState.AVAILABLE
                    else "Arquivo compartilhado por outro registro; será preservado."
                    if asset.shared
                    else "Arquivo fonte externo; será preservado."
                )
                checkbox.setToolTip(f"{asset.path}\n{reason}")
            self.asset_checks[asset.id] = checkbox
            self.asset_layout.addWidget(checkbox)
        if not preview.assets:
            self.asset_layout.addWidget(QLabel("Este mangá não possui arquivos registrados."))
        self.asset_layout.addStretch(1)
        self.asset_scroll.setWidget(self.asset_list)
        layout.addWidget(self.asset_scroll, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.confirm_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.confirm_button.setText("Remover registros")
        self.confirm_button.setAccessibleName("Confirmar remoção dos registros selecionados")
        self.confirm_button.setProperty("primaryAction", True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for checkbox in self.asset_checks.values():
            checkbox.toggled.connect(self._update_confirm_label)

    def selected_asset_ids(self) -> tuple[str, ...]:
        return tuple(
            asset_id
            for asset_id, checkbox in self.asset_checks.items()
            if checkbox.isChecked()
        )

    @staticmethod
    def _asset_description(asset: LibraryAsset) -> str:
        category = _asset_category_label(asset.category)
        status = {
            LibraryAssetState.AVAILABLE: "disponível",
            LibraryAssetState.UNLINKED: "sem vínculo",
            LibraryAssetState.MISSING: "ausente",
            LibraryAssetState.CHANGED: "alterado",
        }[asset.state]
        return f"Excluir {category} · {asset.size_bytes:,} bytes · {asset.path} [{status}]"

    def _update_confirm_label(self, _checked: bool) -> None:
        if self.selected_asset_ids():
            self.confirm_button.setText("Remover registros e arquivos selecionados")
        else:
            self.confirm_button.setText("Remover registros")


class LibraryOrphanDeleteDialog(QDialog):
    def __init__(self, asset: LibraryAsset, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.asset = asset
        self.setWindowTitle("Excluir arquivo sem vínculo")
        self.setModal(True)
        layout = QVBoxLayout(self)
        heading = QLabel("Excluir este arquivo permanentemente?")
        heading.setStyleSheet("font-size: 17px; font-weight: 650;")
        heading.setWordWrap(True)
        details = QLabel(
            f"Categoria: {_asset_category_label(asset.category)}\n"
            f"Tamanho: {asset.size_bytes:,} bytes\n"
            f"Caminho exato: {asset.path}"
        )
        details.setObjectName("libraryOrphanDeleteDetails")
        details.setWordWrap(True)
        note = QLabel("A exclusão é individual e só ocorre após conferir o checksum registrado.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.confirm_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.confirm_button.setText("Excluir este arquivo")
        self.confirm_button.setAccessibleName("Confirmar exclusão deste arquivo sem vínculo")
        self.confirm_button.setProperty("primaryAction", True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(heading)
        layout.addWidget(details)
        layout.addWidget(note)
        layout.addWidget(self.buttons)


class LibraryView(QWidget):
    add_manga_requested = Signal()
    _ALL = "__all__"

    def __init__(
        self,
        runner: OperationRunner | None = None,
        parent: QWidget | None = None,
    ) -> None:
        if isinstance(runner, QWidget) and parent is None:
            parent = runner
            runner = None
        super().__init__(parent)
        self._runner = runner
        self._repository: LibraryRepository | None = None
        self._handlers: dict[str, tuple[str, Callable[[object], None]]] = {}
        self._history_active = False
        self._orphan_mode = False
        self._preferences_loaded = False
        self._completion_notice: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.state_label = QLabel("Conecte a biblioteca local para consultar registros.")
        self.state_label.setObjectName("libraryState")
        self.state_label.setAccessibleName("Estado da biblioteca")

        self.empty_state = EmptyState(
            "Sua biblioteca começa aqui",
            "Adicione um mangá ou importe imagens locais para começar. A biblioteca consulta "
            "somente registros que já foram salvos neste computador.",
            "Adicionar mangá",
        )
        self.empty_state.action_requested.connect(self.add_manga_requested.emit)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("librarySearch")
        self.search_input.setAccessibleName("Pesquisar mangá, autor ou capítulo")
        self.search_input.setPlaceholderText("Mangá, autor, capítulo, número ou volume")
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setObjectName("refreshLibrary")
        self.refresh_button.setAccessibleName("Atualizar biblioteca local")
        self.history_button = QPushButton("Histórico")
        self.history_button.setObjectName("showLibraryHistory")
        self.history_button.setCheckable(True)
        self.history_button.setAccessibleName("Mostrar histórico de operações")
        self.orphan_button = QPushButton("Arquivos sem vínculo")
        self.orphan_button.setObjectName("showUnlinkedLibraryAssets")
        self.orphan_button.setAccessibleName("Mostrar arquivos sem vínculo")
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.refresh_button)
        search_row.addWidget(self.history_button)
        search_row.addWidget(self.orphan_button)

        filter_row = QHBoxLayout()
        self.favorite_filter = QCheckBox("Favoritos")
        self.favorite_filter.setObjectName("libraryFavoriteFilter")
        self.favorite_filter.setAccessibleName("Filtrar somente favoritos")
        self.availability_filter = QComboBox()
        self.availability_filter.setObjectName("libraryAvailabilityFilter")
        self.availability_filter.setAccessibleName("Filtrar disponibilidade")
        self.availability_filter.addItem("Todas as disponibilidades", self._ALL)
        for state, label in (
            (AvailabilityState.DOWNLOADED, "Baixado"),
            (AvailabilityState.PARTIAL, "Parcial"),
            (AvailabilityState.NOT_DOWNLOADED, "Não baixado"),
            (AvailabilityState.IMPORTED, "Importado localmente"),
            (AvailabilityState.MISSING, "Arquivo ausente"),
            (AvailabilityState.ALTERED, "Arquivo alterado"),
        ):
            self.availability_filter.addItem(label, state.value)
        self.download_filter = QComboBox()
        self.download_filter.setObjectName("libraryDownloadFilter")
        self.download_filter.setAccessibleName("Filtrar estado do download")
        self._fill_filter(
            self.download_filter,
            "Todos os downloads",
            ("queued", "running", "paused", "interrupted", "succeeded", "failed", "cancelled"),
        )
        self.export_filter = QComboBox()
        self.export_filter.setObjectName("libraryExportFilter")
        self.export_filter.setAccessibleName("Filtrar estado da exportação")
        self._fill_filter(
            self.export_filter,
            "Todas as exportações",
            ("requested", "running", "completed", "failed", "cancelled", "missing", "altered"),
        )
        self.sort_filter = QComboBox()
        self.sort_filter.setObjectName("librarySort")
        self.sort_filter.setAccessibleName("Ordenar biblioteca")
        for value, label in (
            (LibrarySort.TITLE, "Título"),
            (LibrarySort.ACTIVITY, "Atividade recente"),
            (LibrarySort.STATE, "Disponibilidade"),
            (LibrarySort.CHAPTER, "Capítulo"),
        ):
            self.sort_filter.addItem(label, value.value)
        filter_row.addWidget(self.favorite_filter)
        filter_row.addWidget(self.availability_filter, 1)
        filter_row.addWidget(self.download_filter, 1)
        filter_row.addWidget(self.export_filter, 1)
        filter_row.addWidget(self.sort_filter)

        action_row = QHBoxLayout()
        self.favorite_button = QPushButton("Marcar favorito")
        self.favorite_button.setObjectName("toggleLibraryFavorite")
        self.favorite_button.setAccessibleName("Marcar ou remover favorito")
        self.delete_button = QPushButton("Remover mangá")
        self.delete_button.setObjectName("deleteLibraryManga")
        self.delete_button.setAccessibleName("Revisar remoção do mangá selecionado")
        self.favorite_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        action_row.addWidget(self.favorite_button)
        action_row.addWidget(self.delete_button)
        action_row.addStretch(1)

        self.results_list = QListWidget()
        self.results_list.setObjectName("libraryResults")
        self.results_list.setAccessibleName("Mangás e capítulos da biblioteca local")
        self.results_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.history_list = QListWidget()
        self.history_list.setObjectName("libraryHistory")
        self.history_list.setAccessibleName("Histórico local de operações")
        self.history_list.hide()

        layout.addWidget(self.state_label)
        layout.addLayout(search_row)
        layout.addLayout(filter_row)
        layout.addLayout(action_row)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.results_list, 1)
        layout.addWidget(self.history_list, 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh)
        self.search_input.textChanged.connect(self._search_timer.start)
        self.refresh_button.clicked.connect(self.refresh)
        self.history_button.toggled.connect(self._toggle_history)
        self.orphan_button.clicked.connect(self._toggle_orphans)
        self.favorite_filter.toggled.connect(self._filters_changed)
        for combo in (
            self.availability_filter,
            self.download_filter,
            self.export_filter,
            self.sort_filter,
        ):
            combo.currentIndexChanged.connect(self._filters_changed)
        self.results_list.currentItemChanged.connect(self._selection_changed)
        self.favorite_button.clicked.connect(self._toggle_favorite)
        self.delete_button.clicked.connect(self._request_delete)
        if self._runner is not None:
            self._runner.succeeded.connect(self._on_operation_succeeded)
            self._runner.failed.connect(self._on_operation_failed)
            self._runner.cancelled.connect(self._on_operation_cancelled)

    def bind_services(self, repository: LibraryRepository) -> None:
        self._repository = repository
        if self._runner is None:
            self.state_label.setText("A biblioteca precisa de um executor em segundo plano.")
            return

        def loaded(value: object) -> None:
            if isinstance(value, LibraryPreferences):
                self._apply_preferences(value)
                self._preferences_loaded = True
                self.refresh()

        self._start(
            "preferences",
            lambda _token, _progress: repository.get_preferences(),
            loaded,
            "Não foi possível carregar as preferências da biblioteca.",
        )

    def refresh(self) -> None:
        repository = self._repository
        if repository is None or self._runner is None:
            return
        self._search_timer.stop()
        self.state_label.setText("Consultando registros locais…")
        if self._history_active:
            self._start(
                "history",
                lambda _token, _progress: repository.history(),
                self._show_history,
                "Não foi possível carregar o histórico local.",
            )
            return
        if self._orphan_mode:
            self._start(
                "orphans",
                lambda _token, _progress: repository.list_unlinked_assets(),
                self._show_orphans,
                "Não foi possível carregar os arquivos sem vínculo.",
            )
            return
        query = self._current_query()
        self._persist_preferences(repository)
        self._start(
            "search",
            lambda token, _progress: self._search(repository, query, token),
            self._show_page,
            "Não foi possível consultar a biblioteca local.",
        )

    def _search(
        self,
        repository: LibraryRepository,
        query: LibraryQuery,
        cancellation: CancellationToken,
    ) -> LibraryPage:
        if cancellation.cancelled:
            return LibraryPage((), 0)
        return repository.search(query)

    def _current_query(self) -> LibraryQuery:
        availability_value = self.availability_filter.currentData()
        download_value = self.download_filter.currentData()
        export_value = self.export_filter.currentData()
        return LibraryQuery(
            search_text=self.search_input.text(),
            favorite_only=self.favorite_filter.isChecked(),
            availability=(
                AvailabilityState(availability_value)
                if availability_value != self._ALL
                else None
            ),
            download_state=download_value if download_value != self._ALL else None,
            export_state=export_value if export_value != self._ALL else None,
            sort=LibrarySort(self.sort_filter.currentData()),
        )

    def _persist_preferences(self, repository: LibraryRepository) -> None:
        if not self._preferences_loaded:
            return
        query = self._current_query()
        preferences = LibraryPreferences(
            favorite_only=query.favorite_only,
            availability=query.availability,
            download_state=query.download_state,
            export_state=query.export_state,
            sort=query.sort,
        )
        self._start(
            "save_preferences",
            lambda _token, _progress: repository.save_preferences(preferences),
            lambda _result: None,
            "Não foi possível salvar as preferências da biblioteca.",
        )

    def _show_page(self, value: object) -> None:
        if not isinstance(value, LibraryPage):
            self.state_label.setText("A consulta local retornou um resultado inválido.")
            return
        self.results_list.clear()
        for entry in value.entries:
            if not isinstance(entry, LibraryEntry):
                continue
            state = _availability_label(entry.availability)
            pages = f"{entry.page_count} página(s)"
            if entry.page_total is not None:
                pages += f" de {entry.page_total}"
            details = [state, pages]
            if entry.download_state:
                details.append(f"download: {_state_label(entry.download_state)}")
            if entry.export_state:
                details.append(f"exportação: {_state_label(entry.export_state)}")
            if entry.manga_favorite or entry.chapter_favorite:
                details.append("★ favorito")
            label = f"{entry.display_title}  ·  {'  ·  '.join(details)}"
            if entry.simulated:
                label += "  ·  EXEMPLO OFFLINE"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setToolTip(
                f"{entry.manga_title}, {_availability_label(entry.availability)}"
            )
            self.results_list.addItem(item)
        self.history_list.hide()
        self.results_list.show()
        self.empty_state.setVisible(value.total == 0 and not self.search_input.text().strip())
        if value.total == 0 and self.search_input.text().strip():
            self.state_label.setText("Nenhum resultado para esta busca.")
        else:
            self.state_label.setText(
                f"{value.total} resultado(s) na biblioteca local."
                if value.total
                else "Biblioteca vazia. Adicione um mangá ou importe imagens locais."
            )
        self._append_completion_notice()
        self._selection_changed(self.results_list.currentItem(), None)

    def _show_history(self, value: object) -> None:
        if not isinstance(value, tuple):
            self.state_label.setText("O histórico local retornou um resultado inválido.")
            return
        self.history_list.clear()
        for activity in value:
            if not isinstance(activity, LibraryActivity):
                continue
            kind = {
                ActivityKind.DOWNLOAD: "Download",
                ActivityKind.IMAGE_IMPORT: "Importação de imagens",
                ActivityKind.EXPORT: "Exportação",
            }[activity.kind]
            started = activity.started_at.astimezone().strftime("%d/%m/%Y %H:%M")
            ended = activity.ended_at.astimezone().strftime("%d/%m/%Y %H:%M")
            text = (
                f"{kind} · {activity.identity} · {_state_label(activity.state)}"
                f" · início: {started} · fim: {ended}"
            )
            if activity.reason_code:
                text += f" · Motivo: {activity.reason_code}"
            if activity.location_name:
                text += f" · {activity.location_name}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, activity)
            self.history_list.addItem(item)
        self.results_list.hide()
        self.empty_state.hide()
        self.history_list.show()
        self.state_label.setText(
            f"{len(value)} atividade(s) no histórico local."
            if value
            else "Ainda não há operações no histórico local."
        )
        self.favorite_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.orphan_button.setText("Arquivos sem vínculo")

    def _show_orphans(self, value: object) -> None:
        if not isinstance(value, tuple):
            self.state_label.setText(
                "A lista de arquivos sem vínculo retornou um resultado inválido."
            )
            return
        self.results_list.clear()
        assets = tuple(asset for asset in value if isinstance(asset, LibraryAsset))
        for asset in assets:
            status = _availability_label_from_asset(asset)
            label = (
                f"{asset.path.name} · {_asset_category_label(asset.category)} · "
                f"{asset.size_bytes:,} bytes · {status}"
            )
            if asset.shared:
                label += " · usado por outro registro"
            item = QListWidgetItem(label)
            item.setToolTip(str(asset.path))
            item.setData(Qt.ItemDataRole.UserRole, asset)
            self.results_list.addItem(item)
        self._history_active = False
        self.history_button.blockSignals(True)
        self.history_button.setChecked(False)
        self.history_button.setText("Histórico")
        self.history_button.blockSignals(False)
        self.history_list.hide()
        self.empty_state.hide()
        self.results_list.show()
        self._set_browse_controls_enabled(False)
        self.orphan_button.setText("Biblioteca")
        self.state_label.setText(
            f"{len(assets)} arquivo(s) sem vínculo. Selecione um para revisar a exclusão."
            if assets
            else "Nenhum arquivo sem vínculo."
        )
        self._append_completion_notice()
        self._selection_changed(self.results_list.currentItem(), None)

    def _apply_preferences(self, preferences: LibraryPreferences) -> None:
        widgets = (
            self.favorite_filter,
            self.availability_filter,
            self.download_filter,
            self.export_filter,
            self.sort_filter,
        )
        previous = tuple(widget.blockSignals(True) for widget in widgets)
        self.favorite_filter.setChecked(preferences.favorite_only)
        availability = (
            preferences.availability.value
            if preferences.availability is not None
            else self._ALL
        )
        self._select_combo(self.availability_filter, availability)
        self._select_combo(self.download_filter, preferences.download_state or self._ALL)
        self._select_combo(self.export_filter, preferences.export_state or self._ALL)
        self._select_combo(self.sort_filter, preferences.sort.value)
        for widget, was_blocked in zip(widgets, previous, strict=True):
            widget.blockSignals(was_blocked)

    def _toggle_history(self, active: bool) -> None:
        self._history_active = active
        self._orphan_mode = False
        self.orphan_button.setText("Arquivos sem vínculo")
        if active:
            self.history_button.setText("Biblioteca")
            self._set_browse_controls_enabled(False)
        else:
            self.history_button.setText("Histórico")
            self._set_browse_controls_enabled(True)
        self.refresh()

    def _toggle_orphans(self) -> None:
        if self._orphan_mode:
            self._orphan_mode = False
            self._set_browse_controls_enabled(True)
            self.orphan_button.setText("Arquivos sem vínculo")
            self.refresh()
            return
        self._orphan_mode = True
        self._history_active = False
        self.history_button.blockSignals(True)
        self.history_button.setChecked(False)
        self.history_button.setText("Histórico")
        self.history_button.blockSignals(False)
        self._set_browse_controls_enabled(False)
        self.refresh()

    def _set_browse_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.search_input,
            self.favorite_filter,
            self.availability_filter,
            self.download_filter,
            self.export_filter,
            self.sort_filter,
        ):
            widget.setEnabled(enabled)

    def _filters_changed(self, *_args: object) -> None:
        if not self._history_active:
            self.refresh()

    def _selection_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        entry = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        library_entry = isinstance(entry, LibraryEntry) and self._repository is not None
        orphan_asset = isinstance(entry, LibraryAsset) and self._repository is not None
        self.favorite_button.setEnabled(library_entry)
        self.delete_button.setEnabled(
            library_entry
            or (
                isinstance(entry, LibraryAsset)
                and self._repository is not None
                and entry.state is LibraryAssetState.UNLINKED
                and not entry.shared
                and entry.sha256 is not None
                and (entry.managed or entry.category is LibraryAssetCategory.EXPORT)
            )
        )
        if orphan_asset:
            self.favorite_button.setText("Marcar favorito")
            self.delete_button.setText("Excluir arquivo sem vínculo")
            return
        self.delete_button.setText("Remover mangá")
        if library_entry:
            assert isinstance(entry, LibraryEntry)
            favorite = (
                entry.chapter_favorite
                if entry.chapter_id is not None
                else entry.manga_favorite
            )
            self.favorite_button.setText("Remover favorito" if favorite else "Marcar favorito")

    def _toggle_favorite(self) -> None:
        repository = self._repository
        item = self.results_list.currentItem()
        entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if repository is None or self._runner is None or not isinstance(entry, LibraryEntry):
            return
        current = entry.chapter_favorite if entry.chapter_id is not None else entry.manga_favorite
        self.state_label.setText("Salvando favorito local…")
        self._start(
            "favorite",
            lambda _token, _progress: repository.set_favorite(
                manga_id=entry.manga_id,
                chapter_id=entry.chapter_id,
                favorite=not current,
            ),
            lambda _result: self.refresh(),
            "Não foi possível salvar o favorito local.",
        )

    def _request_delete(self) -> None:
        repository = self._repository
        item = self.results_list.currentItem()
        entry = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(entry, LibraryAsset):
            self._request_delete_orphan(entry)
            return
        if repository is None or not isinstance(entry, LibraryEntry):
            return
        self._start(
            "delete_preview",
            lambda _token, _progress: repository.preview_delete(entry.manga_id),
            self._confirm_delete,
            "Não foi possível preparar a prévia da remoção.",
        )

    def _request_delete_orphan(self, asset: LibraryAsset) -> None:
        repository = self._repository
        if repository is None or self._runner is None:
            return
        if (
            asset.state is not LibraryAssetState.UNLINKED
            or asset.shared
            or asset.sha256 is None
            or (not asset.managed and asset.category is not LibraryAssetCategory.EXPORT)
        ):
            self.state_label.setText("Este arquivo não pode ser excluído com segurança.")
            return
        dialog = LibraryOrphanDeleteDialog(asset, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.state_label.setText("Exclusão cancelada; o arquivo permanece intacto.")
            return
        self._start(
            "delete_orphan",
            lambda _token, _progress: repository.delete_unlinked_assets(
                (asset.id,),
                confirmed=True,
            ),
            self._delete_finished,
            "Não foi possível excluir o arquivo sem vínculo.",
        )

    def _confirm_delete(self, value: object) -> None:
        if not isinstance(value, LibraryDeletionPreview):
            self.state_label.setText("A prévia da remoção não pôde ser validada.")
            return
        dialog = LibraryDeleteDialog(value, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.state_label.setText("Remoção cancelada; nenhum registro ou arquivo foi alterado.")
            return
        repository = self._repository
        if repository is None:
            return
        selected = dialog.selected_asset_ids()
        self.state_label.setText("Aplicando a remoção confirmada…")
        self._start(
            "delete",
            lambda _token, _progress: repository.delete_scope(
                value,
                asset_ids=selected,
                confirmed=True,
            ),
            self._delete_finished,
            "A remoção não foi concluída; revise o estado da biblioteca.",
        )

    def _delete_finished(self, value: object) -> None:
        state = {
            "completed": "concluída",
            "partial": "parcial",
            "failed": "falhou",
        }.get(getattr(value, "state", "failed"), "falhou")
        removed_records = getattr(value, "removed_record_count", 0)
        removed_files = getattr(value, "removed_file_count", 0)
        preserved_files = getattr(value, "preserved_file_count", 0)
        self._completion_notice = (
            f"Remoção {state}: {removed_records} registro(s), "
            f"{removed_files} arquivo(s) removido(s), {preserved_files} preservado(s)."
        )
        self.refresh()

    def _append_completion_notice(self) -> None:
        if self._completion_notice is not None:
            self.state_label.setText(f"{self._completion_notice} {self.state_label.text()}")
            self._completion_notice = None

    def _start(
        self,
        kind: str,
        operation: BackgroundOperation,
        callback: Callable[[object], None],
        failure_message: str,
    ) -> str | None:
        if self._runner is None:
            self.state_label.setText(failure_message)
            return None
        operation_id = self._runner.start(operation)
        self._handlers[operation_id] = (failure_message, callback)
        return operation_id

    def _on_operation_succeeded(self, operation_id: str, value: object) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is not None:
            _message, callback = handler
            callback(value)

    def _on_operation_failed(self, operation_id: str, code: str) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is None:
            return
        message, _callback = handler
        self.state_label.setText(f"{message} Código técnico: {code}.")

    def _on_operation_cancelled(self, operation_id: str) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is not None:
            self.state_label.setText("Consulta da biblioteca cancelada.")

    @staticmethod
    def _fill_filter(combo: QComboBox, all_label: str, states: tuple[str, ...]) -> None:
        combo.addItem(all_label, LibraryView._ALL)
        for state in states:
            combo.addItem(_state_label(state), state)

    @staticmethod
    def _select_combo(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)


def _availability_label(state: AvailabilityState) -> str:
    return {
        AvailabilityState.DOWNLOADED: "Baixado",
        AvailabilityState.PARTIAL: "Parcial",
        AvailabilityState.NOT_DOWNLOADED: "Não baixado",
        AvailabilityState.IMPORTED: "Importado localmente",
        AvailabilityState.MISSING: "Arquivo ausente",
        AvailabilityState.ALTERED: "Arquivo alterado",
    }[state]


def _availability_label_from_asset(asset: LibraryAsset) -> str:
    return {
        LibraryAssetState.AVAILABLE: "Disponível",
        LibraryAssetState.UNLINKED: "Sem vínculo",
        LibraryAssetState.MISSING: "Ausente",
        LibraryAssetState.CHANGED: "Alterado",
    }[asset.state]


def _asset_category_label(category: LibraryAssetCategory) -> str:
    return {
        LibraryAssetCategory.ORIGINAL: "Original gerenciado",
        LibraryAssetCategory.PROCESSED: "Imagem processada",
        LibraryAssetCategory.DOWNLOAD: "Página baixada",
        LibraryAssetCategory.EXPORT: "Export registrado",
    }[category]


def _state_label(state: str) -> str:
    return {
        "queued": "Na fila",
        "running": "Em andamento",
        "paused": "Pausado",
        "interrupted": "Interrompido",
        "succeeded": "Concluído",
        "completed": "Concluído",
        "failed": "Falhou",
        "cancelled": "Cancelado",
        "requested": "Solicitado",
        "staging": "Preparando",
    }.get(state, state.replace("_", " ").capitalize())
