"""Coordena ciclo de vida e preferências locais fora da thread gráfica."""

from __future__ import annotations

from collections.abc import Callable
from logging import Logger

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from manga_to_kindle.application.errors import StartupErrorInfo, describe_startup_error
from manga_to_kindle.application.lifecycle import ApplicationRuntime
from manga_to_kindle.application.ui.theme_mode import ThemeMode
from manga_to_kindle.infrastructure.config.settings import AppSettings
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.presentation.qt.exception_handler import QtExceptionReporter
from manga_to_kindle.presentation.qt.main_window import MainWindow
from manga_to_kindle.presentation.qt.startup import ShutdownWorker, StartupWorker
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    ProgressReporter,
)

type SettingsWriter = Callable[[AppPaths, AppSettings], None]


class ApplicationController(QObject):
    """Executa bootstrap, preferências e encerramento com workers Qt."""

    startup_finished = Signal()
    shutdown_finished = Signal()

    def __init__(
        self,
        application: QApplication,
        window: MainWindow,
        paths: AppPaths | None = None,
        settings_writer: SettingsWriter | None = None,
    ) -> None:
        super().__init__(application)
        self._application = application
        self._window = window
        self._paths = paths or AppPaths.from_qstandardpaths()
        self._settings_writer = settings_writer
        self._runtime: ApplicationRuntime | None = None
        self._reporter: QtExceptionReporter | None = None
        self._threads: dict[int, QThread] = {}
        self._workers: dict[int, StartupWorker | ShutdownWorker] = {}
        self._close_requested = False
        self._shutdown_started = False
        self._startup_error: StartupErrorInfo | None = None
        self._theme_operation_id: str | None = None
        self._saving_theme: ThemeMode | None = None
        self._pending_theme: ThemeMode | None = None
        self._operation_runner = window.operation_runner
        self._window.close_requested.connect(self._begin_shutdown)
        self._window.theme_change_requested.connect(self._request_theme_save)
        self._operation_runner.succeeded.connect(self._theme_save_succeeded)
        self._operation_runner.failed.connect(self._theme_save_failed)
        self._operation_runner.idle.connect(self._on_operations_idle)

    @property
    def runtime(self) -> ApplicationRuntime | None:
        return self._runtime

    def start(self) -> None:
        worker = StartupWorker(self._paths)
        self._start_worker(worker)

    def _start_worker(self, worker: StartupWorker | ShutdownWorker) -> None:
        thread = QThread(self)
        worker_key = id(thread)
        self._threads[worker_key] = thread
        self._workers[worker_key] = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        if isinstance(worker, StartupWorker):
            worker.succeeded.connect(self._startup_succeeded)
            worker.failed.connect(self._startup_failed)
        else:
            worker.succeeded.connect(self._shutdown_succeeded)
            worker.failed.connect(self._shutdown_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda key=worker_key: self._release_worker(key))
        thread.start()

    def _release_worker(self, worker_key: int) -> None:
        self._workers.pop(worker_key, None)
        self._threads.pop(worker_key, None)

    @Slot(object)
    def _startup_succeeded(self, runtime: ApplicationRuntime) -> None:
        if self._runtime is not None:
            return
        self._runtime = runtime
        self._window.set_status("Fundação local pronta. Os dados permanecem neste computador.")
        if self._pending_theme is None:
            self._window.set_theme(runtime.settings.theme)
        else:
            self._window.set_theme(self._pending_theme)
            if not self._close_requested:
                self._start_pending_theme_save()
        self._reporter = QtExceptionReporter(runtime.logger)
        self._reporter.reported.connect(self._show_unhandled_error)
        self._reporter.install()
        self.startup_finished.emit()
        if self._close_requested:
            self._begin_shutdown()

    @Slot(object)
    def _startup_failed(self, error: Exception) -> None:
        self._startup_error = describe_startup_error(error)
        self._window.set_status(self._startup_error.message)
        QMessageBox.critical(self._window, "Falha ao iniciar", self._startup_error.message)
        self._window.allow_close()
        self.startup_finished.emit()

    @Slot(str)
    def _request_theme_save(self, theme_value: str) -> None:
        self._pending_theme = "dark" if theme_value == "dark" else "light"
        if self._runtime is not None:
            self._start_pending_theme_save()

    def _start_pending_theme_save(self) -> None:
        runtime = self._runtime
        theme = self._pending_theme
        settings_writer = self._settings_writer
        if (
            runtime is None
            or theme is None
            or self._theme_operation_id is not None
            or settings_writer is None
        ):
            if self._settings_writer is None and theme is not None:
                self._window.set_status("Tema aplicado nesta sessão; persistência indisponível.")
            return
        updated_settings = runtime.settings.model_copy(update={"theme": theme})
        self._saving_theme = theme

        def persist(
            cancellation: CancellationToken,
            _: ProgressReporter,
        ) -> AppSettings:
            if cancellation.cancelled:
                return runtime.settings
            settings_writer(runtime.paths, updated_settings)
            return updated_settings

        operation: BackgroundOperation = persist
        self._theme_operation_id = self._operation_runner.start(operation)
        self._pending_theme = None

    @Slot(str, object)
    def _theme_save_succeeded(self, operation_id: str, result: object) -> None:
        if operation_id != self._theme_operation_id:
            return
        self._theme_operation_id = None
        self._saving_theme = None
        if isinstance(result, AppSettings) and self._runtime is not None:
            self._runtime.settings = result
        if self._pending_theme is not None:
            self._start_pending_theme_save()

    @Slot(str, str)
    def _theme_save_failed(self, operation_id: str, code: str) -> None:
        if operation_id != self._theme_operation_id:
            return
        self._theme_operation_id = None
        self._saving_theme = None
        logger: Logger | None = self._runtime.logger if self._runtime is not None else None
        if logger is not None:
            logger.error("theme preference persistence failed code=%s", code)
        if self._pending_theme is not None:
            self._start_pending_theme_save()
        else:
            self._window.set_status(
                "Tema aplicado nesta sessão, mas não foi possível salvar a preferência."
            )

    @Slot()
    def _begin_shutdown(self) -> None:
        self._close_requested = True
        if self._runtime is None:
            if self._startup_error is not None:
                self._window.allow_close()
                self._window.close()
            else:
                self._window.set_status(
                    "Aguarde a preparação local terminar para encerrar com segurança."
                )
            return
        self._window.setEnabled(False)
        if self._operation_runner.active_count:
            self._window.set_status("Cancelando operações simuladas antes de encerrar…")
            self._operation_runner.cancel_all()
            return
        self._start_shutdown()

    @Slot()
    def _on_operations_idle(self) -> None:
        if self._close_requested and self._runtime is not None:
            self._start_shutdown()

    def _start_shutdown(self) -> None:
        if self._runtime is None or self._shutdown_started:
            return
        self._shutdown_started = True
        self._window.set_status("Encerrando operações locais com segurança…")
        if self._reporter is not None:
            self._reporter.restore()
        worker = ShutdownWorker(self._runtime)
        self._start_worker(worker)

    @Slot()
    def _shutdown_succeeded(self) -> None:
        self._runtime = None
        self._window.allow_close()
        self._window.close()
        self.shutdown_finished.emit()

    @Slot(object)
    def _shutdown_failed(self, error: Exception) -> None:
        info = describe_startup_error(error)
        self._shutdown_started = False
        self._close_requested = False
        self._window.setEnabled(True)
        self._window.set_status(info.message)
        QMessageBox.critical(self._window, "Falha ao encerrar", info.message)

    @Slot(object)
    def _show_unhandled_error(self, error: StartupErrorInfo) -> None:
        QMessageBox.critical(self._window, "Erro inesperado", error.message)

