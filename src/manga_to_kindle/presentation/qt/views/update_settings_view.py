"""Estado local, controles de opt-in e avisos de catálogo F010."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.updates.preferences import SaveUpdatePreference
from manga_to_kindle.application.updates.refresh_manga_catalog import (
    RefreshMangaCatalog,
    RefreshMangaCatalogResult,
    UpdateTrigger,
)
from manga_to_kindle.application.updates.scheduler import (
    PeriodicUpdateScheduler,
    ScheduledUpdate,
)
from manga_to_kindle.domain.providers import CatalogUpdateProvider, UnsupportedSource
from manga_to_kindle.domain.updates import (
    ChapterNotice,
    UpdateMangaStatus,
    UpdatePreference,
)
from manga_to_kindle.infrastructure.persistence.update_repository import UpdateRepository
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    OperationRunner,
    ProgressReporter,
)


class _OperationHandler:
    def __init__(
        self,
        success: Callable[[object], None],
        failure: Callable[[str], None],
        finished: Callable[[], None],
    ) -> None:
        self.success = success
        self.failure = failure
        self.finished = finished


class UpdateSettingsView(QWidget):
    _MAX_INTERVAL_MINUTES = 525_600
    _SCHEDULER_POLL_MILLISECONDS = 30_000

    def __init__(
        self,
        runner: OperationRunner | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._repository: UpdateRepository | None = None
        self._providers: ProviderRegistry | None = None
        self._save_preference: SaveUpdatePreference | None = None
        self._refresh_catalog: RefreshMangaCatalog | None = None
        self._scheduler = PeriodicUpdateScheduler()
        self._statuses: tuple[UpdateMangaStatus, ...] = ()
        self._handlers: dict[str, _OperationHandler] = {}
        self._active_manga_ids: set[UUID] = set()
        self._polling_scheduler = False
        self._scheduler_generation = 0
        self._status_refresh_pending = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)
        intro = QLabel(
            "Atualizações consultam somente fontes com autorização e limites documentados. "
            "O monitoramento começa desligado. Avisos locais nunca baixam nem enviam capítulos."
        )
        intro.setWordWrap(True)
        intro.setObjectName("updateSettingsIntro")
        layout.addWidget(intro)

        self.state_label = QLabel("O estado das fontes locais será carregado após a inicialização.")
        self.state_label.setObjectName("updateSettingsState")
        self.state_label.setWordWrap(True)
        layout.addWidget(self.state_label)

        self.table = QTableWidget(0, 4)
        self.table.setObjectName("chapterUpdateStatusTable")
        self.table.setHorizontalHeaderLabels(
            (
                "Mangá",
                "Fonte e última verificação",
                "Preferências locais",
                "Ações",
            )
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel("Nenhum catálogo local foi registrado ainda.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)
        self.refresh_button = QPushButton("Atualizar estado")
        self.refresh_button.setObjectName("refreshUpdateStatuses")
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignRight)

        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.setInterval(self._SCHEDULER_POLL_MILLISECONDS)
        self._scheduler_timer.timeout.connect(self._poll_scheduler)

        if runner is not None:
            runner.succeeded.connect(self._on_operation_succeeded)
            runner.failed.connect(self._on_operation_failed)
            runner.cancelled.connect(self._on_operation_cancelled)

    def bind_services(
        self,
        repository: UpdateRepository,
        providers: ProviderRegistry,
        save_preference: SaveUpdatePreference,
        refresh_catalog: RefreshMangaCatalog,
    ) -> None:
        self._repository = repository
        self._providers = providers
        self._save_preference = save_preference
        self._refresh_catalog = refresh_catalog
        self.refresh()

    def refresh(self) -> None:
        repository = self._repository
        if repository is None:
            self.state_label.setText("A persistência de atualizações ainda não está disponível.")
            return
        if self._status_refresh_pending:
            return
        self._status_refresh_pending = True

        def finished() -> None:
            self._status_refresh_pending = False

        self._start(
            lambda _token, _progress: repository.list_statuses(),
            self._show_statuses,
            lambda code: self.state_label.setText(
                f"Não foi possível carregar o estado local. Código técnico: {code}."
            ),
            finished=finished,
        )

    def stop_scheduler(self) -> None:
        self._scheduler_generation += 1
        self._scheduler_timer.stop()

    def _show_statuses(self, value: object) -> None:
        if not isinstance(value, tuple) or not all(
            isinstance(status, UpdateMangaStatus) for status in value
        ):
            self.state_label.setText("O estado salvo não pôde ser validado.")
            return
        self._statuses = value
        self.table.setRowCount(len(value))
        for row, status in enumerate(value):
            self._populate_row(row, status)
        self.empty_label.setVisible(not value)
        self.table.setVisible(bool(value))
        self.state_label.setText(
            "Estado local atualizado. Consultas externas só aparecem habilitadas "
            "quando a fonte está autorizada."
        )
        self._sync_scheduler_timer()

    def _populate_row(self, row: int, status: UpdateMangaStatus) -> None:
        title_cell = QWidget()
        title_layout = QVBoxLayout(title_cell)
        title_layout.setContentsMargins(4, 4, 4, 4)
        title_label = QLabel(status.title)
        title_label.setStyleSheet("font-weight: 650;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(QLabel(f"{status.chapter_count} capítulo(s) no catálogo"))
        self.table.setCellWidget(row, 0, title_cell)

        provider, availability = self._provider_status(status)
        source_label = QLabel(f"{availability}\n{_last_check_label(status)}")
        source_label.setWordWrap(True)
        self.table.setCellWidget(row, 1, source_label)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(3)
        self.table.setCellWidget(row, 2, controls)
        can_refresh = provider is not None
        periodic_minimum = (
            provider.capabilities.minimum_catalog_update_interval_seconds
            if provider is not None and provider.capabilities.periodic_catalog_updates_enabled
            else None
        )
        can_monitor = can_refresh and periodic_minimum is not None
        monitor = QCheckBox("Monitoramento periódico")
        monitor.setObjectName(f"monitorUpdates_{status.manga_id}")
        monitor.setAccessibleName(f"Monitorar capítulos de {status.title}")
        monitor.setChecked(status.preference.enabled)
        monitor.setEnabled(can_monitor)
        monitor.setToolTip(
            "Exige consulta periódica autorizada e intervalo mínimo documentado."
            if not can_monitor
            else ""
        )
        controls_layout.addWidget(monitor)

        interval = QSpinBox()
        interval.setObjectName(f"updateInterval_{status.manga_id}")
        interval.setAccessibleName(f"Intervalo de atualização de {status.title}, em minutos")
        minimum_minutes = max(1, ceil((periodic_minimum or 60) / 60))
        interval.setRange(minimum_minutes, self._MAX_INTERVAL_MINUTES)
        stored_minutes = ceil((status.preference.interval_seconds or minimum_minutes * 60) / 60)
        interval.setValue(max(minimum_minutes, min(stored_minutes, self._MAX_INTERVAL_MINUTES)))
        interval.setEnabled(can_monitor)
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Intervalo (min)"))
        interval_layout.addWidget(interval)
        controls_layout.addLayout(interval_layout)

        notifications = QCheckBox(f"Avisos locais ({status.unread_notice_count} não lido(s))")
        notifications.setObjectName(f"chapterNotices_{status.manga_id}")
        notifications.setAccessibleName(f"Avisos locais de capítulos de {status.title}")
        notifications.setChecked(status.preference.notifications_enabled)
        notifications.setEnabled(status.provider_id is not None)
        controls_layout.addWidget(notifications)

        save_button = QPushButton("Salvar preferências")
        save_button.setObjectName(f"saveUpdatePreference_{status.manga_id}")
        save_button.setEnabled(can_monitor or status.provider_id is not None)

        def save_preferences(
            _checked: bool = False,
            manga_id: UUID = status.manga_id,
            monitor_box: QCheckBox = monitor,
            interval_input: QSpinBox = interval,
            notification_box: QCheckBox = notifications,
        ) -> None:
            self._save_manga_preference(
                manga_id,
                monitor_box.isChecked(),
                interval_input.value() * 60,
                notification_box.isChecked(),
            )

        save_button.clicked.connect(save_preferences)
        controls_layout.addWidget(save_button)

        actions = QWidget()
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        update_button = QPushButton("Atualizar")
        update_button.setObjectName(f"manualUpdate_{status.manga_id}")
        update_button.setEnabled(can_refresh and status.manga_id not in self._active_manga_ids)
        update_button.setToolTip(
            "A fonte não tem consulta remota autorizada e completa."
            if not can_refresh
            else "Consulta o catálogo; não baixa nem envia capítulos."
        )
        update_button.clicked.connect(
            lambda _checked=False, manga_id=status.manga_id: self._refresh_manga(manga_id)
        )
        actions_layout.addWidget(update_button)

        read_button = QPushButton("Ver avisos")
        read_button.setObjectName(f"readNotices_{status.manga_id}")
        read_button.setEnabled(status.unread_notice_count > 0)
        read_button.clicked.connect(
            lambda _checked=False, manga_id=status.manga_id, title=status.title: self._view_notices(
                manga_id,
                title,
            )
        )
        actions_layout.addWidget(read_button)
        self.table.setCellWidget(row, 3, actions)
        self.table.setRowHeight(row, 145)

    def _provider_status(
        self,
        status: UpdateMangaStatus,
    ) -> tuple[CatalogUpdateProvider | None, str]:
        if status.simulated:
            return None, "Demonstração; atualização bloqueada"
        if status.provider_id is None:
            return None, "Sem origem de catálogo"
        registry = self._providers
        if registry is None:
            return None, "Registro de fontes indisponível"
        try:
            provider = registry.by_id(status.provider_id)
        except UnsupportedSource:
            return None, "Fonte não configurada"
        if provider.capabilities.simulated:
            return None, "Demonstração; atualização bloqueada"
        if not provider.capabilities.catalog_query_enabled:
            return None, "Sem autorização de consulta"
        if not isinstance(provider, CatalogUpdateProvider):
            return None, "Consulta completa indisponível"
        if status.last_check is None:
            return provider, "Consulta autorizada"
        return provider, _last_check_label(status)

    def _save_manga_preference(
        self,
        manga_id: UUID,
        enabled: bool,
        interval_seconds: int,
        notifications_enabled: bool,
    ) -> None:
        save = self._save_preference
        if save is None:
            self.state_label.setText("As preferências de atualização não estão disponíveis.")
            return
        preference = UpdatePreference(
            manga_id=manga_id,
            enabled=enabled,
            interval_seconds=interval_seconds,
            notifications_enabled=notifications_enabled,
        )
        self._scheduler_generation += 1
        self._scheduler_timer.stop()

        def success(value: object) -> None:
            if isinstance(value, UpdatePreference):
                self.state_label.setText("Preferências locais salvas.")
                self.refresh()
            else:
                self.state_label.setText("O estado da preferência salva não pôde ser validado.")

        def failure(code: str) -> None:
            self.state_label.setText(
                "A fonte não autoriza o monitoramento ou o intervalo escolhido. "
                f"Código técnico: {code}."
            )
            self.refresh()

        self._start(
            lambda token, _progress: _execute_if_not_cancelled(
                token,
                lambda: save.execute(preference),
            ),
            success,
            failure,
        )

    def _refresh_manga(
        self,
        manga_id: UUID,
        *,
        scheduled: ScheduledUpdate | None = None,
    ) -> None:
        refresh = self._refresh_catalog
        if refresh is None or manga_id in self._active_manga_ids:
            if scheduled is not None:
                self._scheduler.release(scheduled)
            return
        self._active_manga_ids.add(manga_id)
        update_button = self.findChild(QPushButton, f"manualUpdate_{manga_id}")
        if update_button is not None:
            update_button.setEnabled(False)
        self.state_label.setText("Consultando o catálogo completo autorizado…")

        def finished() -> None:
            self._active_manga_ids.discard(manga_id)
            if scheduled is not None:
                self._scheduler.release(scheduled)
            self.refresh()

        def success(value: object) -> None:
            if not isinstance(value, RefreshMangaCatalogResult):
                self.state_label.setText("O resultado da atualização não pôde ser validado.")
                return
            self.state_label.setText(
                f"Catálogo atualizado: {value.check.new_chapter_count} capítulo(s) novo(s). "
                "Nenhum download ou envio foi iniciado."
            )

        def failure(code: str) -> None:
            self.state_label.setText(
                f"Catálogo anterior preservado; atualização indisponível. Código técnico: {code}."
            )

        def operation(token: CancellationToken, _progress: ProgressReporter) -> object:
            trigger = UpdateTrigger.SCHEDULED if scheduled is not None else UpdateTrigger.MANUAL
            return refresh.execute(
                manga_id,
                trigger=trigger,
                is_cancelled=lambda: token.cancelled,
            )

        self._start(operation, success, failure, finished=finished)

    def _mark_notices_read(
        self,
        manga_id: UUID,
        notice_ids: tuple[UUID, ...] | None = None,
    ) -> None:
        repository = self._repository
        if repository is None:
            return

        def mark(_token: CancellationToken, _progress: ProgressReporter) -> int:
            if notice_ids is None:
                selected_ids = tuple(
                    notice.id for notice in repository.list_notices(manga_id, unread_only=True)
                )
            else:
                selected_ids = notice_ids
            return sum(repository.mark_notice_read(notice_id) for notice_id in selected_ids)

        def success(value: object) -> None:
            count = value if isinstance(value, int) else 0
            self.state_label.setText(f"{count} aviso(s) local(is) marcado(s) como lido(s).")
            self.refresh()

        self._start(
            mark,
            success,
            lambda code: self.state_label.setText(
                f"Não foi possível marcar os avisos. Código técnico: {code}."
            ),
        )

    def _view_notices(self, manga_id: UUID, manga_title: str) -> None:
        repository = self._repository
        if repository is None:
            return

        def show(value: object) -> None:
            if not isinstance(value, tuple) or not all(
                isinstance(notice, ChapterNotice) for notice in value
            ):
                self.state_label.setText("Os avisos locais não puderam ser validados.")
                return
            if not value:
                self.state_label.setText("Não há avisos novos para este mangá.")
                self.refresh()
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Novos capítulos · {manga_title}")
            dialog.setModal(True)
            dialog.resize(540, 400)
            layout = QVBoxLayout(dialog)
            heading = QLabel(f"{len(value)} capítulo(s) novo(s) encontrado(s)")
            heading.setStyleSheet("font-size: 17px; font-weight: 650;")
            layout.addWidget(heading)
            notice_list = QListWidget(dialog)
            notice_list.setAccessibleName(f"Novos capítulos de {manga_title}")
            for notice in value:
                notice_list.addItem(
                    f"{notice.chapter_title_snapshot} · "
                    f"{notice.created_at.astimezone().strftime('%d/%m/%Y %H:%M')}"
                )
            layout.addWidget(notice_list, 1)
            buttons = QHBoxLayout()
            close_button = QPushButton("Fechar")
            mark_button = QPushButton("Marcar como lidos")
            mark_button.setProperty("primaryAction", True)
            close_button.clicked.connect(dialog.reject)
            mark_button.clicked.connect(dialog.accept)
            buttons.addWidget(close_button)
            buttons.addStretch(1)
            buttons.addWidget(mark_button)
            layout.addLayout(buttons)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._mark_notices_read(
                    manga_id,
                    tuple(notice.id for notice in value),
                )

        self._start(
            lambda _token, _progress: repository.list_notices(
                manga_id,
                unread_only=True,
            ),
            show,
            lambda code: self.state_label.setText(
                f"Não foi possível abrir os avisos locais. Código técnico: {code}."
            ),
        )

    def _poll_scheduler(self) -> None:
        repository = self._repository
        providers = self._providers
        if repository is None or providers is None or self._polling_scheduler:
            return
        self._polling_scheduler = True
        generation = self._scheduler_generation

        def poll(_token: CancellationToken, _progress: ProgressReporter) -> ScheduledUpdate | None:
            return self._scheduler.claim_due(
                repository.list_statuses(),
                providers,
                datetime.now(UTC),
            )

        def success(value: object) -> None:
            if isinstance(value, ScheduledUpdate):
                if (
                    generation != self._scheduler_generation
                    or value.manga_id in self._active_manga_ids
                ):
                    self._scheduler.release(value)
                else:
                    self._refresh_manga(value.manga_id, scheduled=value)

        def finished() -> None:
            self._polling_scheduler = False

        self._start(poll, success, lambda _code: None, finished=finished)

    def _sync_scheduler_timer(self) -> None:
        if any(
            status.preference.enabled
            and (provider := self._provider_status(status)[0]) is not None
            and provider.capabilities.periodic_catalog_updates_enabled
            for status in self._statuses
        ):
            if not self._scheduler_timer.isActive():
                self._scheduler_timer.start()
        else:
            self._scheduler_timer.stop()

    def _start(
        self,
        operation: BackgroundOperation,
        success: Callable[[object], None],
        failure: Callable[[str], None],
        *,
        finished: Callable[[], None] = lambda: None,
    ) -> str | None:
        runner = self._runner
        if runner is None:
            self.state_label.setText("Workers Qt não estão disponíveis.")
            finished()
            return None
        operation_id = runner.start(operation)
        self._handlers[operation_id] = _OperationHandler(success, failure, finished)
        return operation_id

    def _on_operation_succeeded(self, operation_id: str, result: object) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is None:
            return
        try:
            handler.success(result)
        finally:
            handler.finished()

    def _on_operation_failed(self, operation_id: str, code: str) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is None:
            return
        try:
            handler.failure(code)
        finally:
            handler.finished()

    def _on_operation_cancelled(self, operation_id: str) -> None:
        handler = self._handlers.pop(operation_id, None)
        if handler is None:
            return
        try:
            handler.failure("UPDATE_CANCELLED")
        finally:
            handler.finished()


def _execute_if_not_cancelled(
    token: CancellationToken,
    action: Callable[[], object],
) -> object:
    if token.cancelled:
        return None
    return action()


def _last_check_label(status: UpdateMangaStatus) -> str:
    check = status.last_check
    if check is None:
        return "Ainda não verificado"
    label = {
        "succeeded": "Concluída",
        "failed": "Falhou",
        "rate_limited": "Limite temporário",
        "cancelled": "Cancelada",
        "unsupported": "Não autorizada",
    }.get(check.status.value, "Indisponível")
    when = check.finished_at or check.started_at
    return f"{label} · {when.astimezone().strftime('%d/%m/%Y %H:%M')}"
