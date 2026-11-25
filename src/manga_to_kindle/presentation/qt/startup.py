"""Workers Qt para operações locais da inicialização e do encerramento."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from manga_to_kindle.application.bootstrap import bootstrap_application
from manga_to_kindle.application.lifecycle import ApplicationRuntime
from manga_to_kindle.infrastructure.paths import AppPaths


class StartupWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self._paths = paths

    @Slot()
    def run(self) -> None:
        try:
            self.succeeded.emit(bootstrap_application(self._paths))
        except Exception as exc:
            self.failed.emit(exc)
        finally:
            self.finished.emit()


class ShutdownWorker(QObject):
    succeeded = Signal()
    failed = Signal(object)
    finished = Signal()

    def __init__(self, runtime: ApplicationRuntime) -> None:
        super().__init__()
        self._runtime = runtime

    @Slot()
    def run(self) -> None:
        try:
            self._runtime.shutdown()
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(exc)
        finally:
            self.finished.emit()
