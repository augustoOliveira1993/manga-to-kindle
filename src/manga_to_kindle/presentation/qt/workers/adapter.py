"""Despacho de operações fora da thread gráfica com sinais tipados."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from uuid import uuid4

from PySide6.QtCore import QObject, QThread, Signal, Slot

type ProgressReporter = Callable[[int, int | None, str], None]
type BackgroundOperation = Callable[[CancellationToken, ProgressReporter], object]


class CancellationToken:
    """Sinal cooperativo e seguro entre a interface e uma operação em worker."""

    def __init__(self) -> None:
        self._event = Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def wait(self, timeout_seconds: float) -> bool:
        return self._event.wait(timeout_seconds)


class OperationWorker(QObject):
    started = Signal(str)
    progress = Signal(str, int, object, str)
    succeeded = Signal(str, object)
    failed = Signal(str, str)
    cancelled = Signal(str)
    finished = Signal(str)

    def __init__(
        self,
        operation_id: str,
        operation: BackgroundOperation,
        cancellation: CancellationToken,
    ) -> None:
        super().__init__()
        self._operation_id = operation_id
        self._operation = operation
        self._cancellation = cancellation

    @Slot()
    def run(self) -> None:
        self.started.emit(self._operation_id)
        try:
            result = self._operation(self._cancellation, self._report_progress)
        except Exception as error:
            code = getattr(error, "code", "OPERATION_FAILED")
            candidate = str(code).upper()
            safe_code = (
                candidate
                if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", candidate)
                else "OPERATION_FAILED"
            )
            self.failed.emit(self._operation_id, safe_code)
        else:
            if self._cancellation.cancelled:
                self.cancelled.emit(self._operation_id)
            else:
                self.succeeded.emit(self._operation_id, result)
        finally:
            self.finished.emit(self._operation_id)

    def _report_progress(self, completed: int, total: int | None, stage: str) -> None:
        safe_completed = max(0, completed)
        safe_total = max(0, total) if total is not None else None
        self.progress.emit(self._operation_id, safe_completed, safe_total, stage)


@dataclass(slots=True)
class _WorkerHandle:
    thread: QThread
    worker: OperationWorker
    cancellation: CancellationToken


class OperationRunner(QObject):
    """Mantém workers vivos e retransmite resultados apenas por sinais Qt."""

    started = Signal(str)
    progress = Signal(str, int, object, str)
    succeeded = Signal(str, object)
    failed = Signal(str, str)
    cancelled = Signal(str)
    finished = Signal(str)
    idle = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workers: dict[str, _WorkerHandle] = {}

    @property
    def active_count(self) -> int:
        return len(self._workers)

    def start(self, operation: BackgroundOperation) -> str:
        operation_id = str(uuid4())
        cancellation = CancellationToken()
        worker = OperationWorker(operation_id, operation, cancellation)
        thread = QThread(self)
        thread.setProperty("operationId", operation_id)
        self._workers[operation_id] = _WorkerHandle(thread, worker, cancellation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.started.connect(self.started.emit)
        worker.progress.connect(self.progress.emit)
        worker.succeeded.connect(self.succeeded.emit)
        worker.failed.connect(self.failed.emit)
        worker.cancelled.connect(self.cancelled.emit)
        worker.finished.connect(self.finished.emit)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._release_finished_thread)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        return operation_id

    def cancel(self, operation_id: str) -> bool:
        handle = self._workers.get(operation_id)
        if handle is None:
            return False
        handle.cancellation.cancel()
        return True

    def cancel_all(self) -> None:
        for handle in tuple(self._workers.values()):
            handle.cancellation.cancel()

    @Slot()
    def _release_finished_thread(self) -> None:
        thread = self.sender()
        if not isinstance(thread, QThread):
            return
        operation_id = thread.property("operationId")
        if not isinstance(operation_id, str):
            return
        thread.wait()
        self._workers.pop(operation_id, None)
        if not self._workers:
            self.idle.emit()


