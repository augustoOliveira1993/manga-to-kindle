from __future__ import annotations

import threading

import pytest
from PySide6.QtCore import QEvent, QEventLoop, QTimer

from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


@pytest.fixture
def operation_runner(qt_core_app):
    runner = OperationRunner()
    yield runner
    if runner.active_count:
        _wait_for_idle(runner, qt_core_app)
    runner.deleteLater()
    qt_core_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_core_app.processEvents()


def _wait_for_idle(runner: OperationRunner, qt_core_app) -> None:
    if runner.active_count == 0:
        return
    event_loop = QEventLoop()
    poll_timer = QTimer()
    poll_timer.setInterval(5)
    poll_timer.timeout.connect(
        lambda: event_loop.quit() if runner.active_count == 0 else None
    )
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(event_loop.quit)
    poll_timer.start()
    timeout_timer.start(3000)
    event_loop.exec()
    poll_timer.stop()
    timeout_timer.stop()
    qt_core_app.processEvents()
    assert runner.active_count == 0


def test_operation_runs_on_background_thread_and_reports_progress(
    qt_core_app, operation_runner: OperationRunner
) -> None:
    runner = operation_runner
    event_loop = QEventLoop()
    worker_thread_ids: list[int] = []
    progress_events: list[tuple[int, int | None, str]] = []
    result: list[object] = []
    runner.progress.connect(
        lambda operation_id, completed, total, stage: progress_events.append(
            (completed, total, stage)
        )
    )
    runner.succeeded.connect(lambda _operation_id, value: (result.append(value), event_loop.quit()))

    def work(_cancellation, report):
        worker_thread_ids.append(threading.get_ident())
        report(1, 1, "Etapa simulada")
        return "concluído"

    runner.start(work)
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(event_loop.quit)
    timeout_timer.start(3000)
    event_loop.exec()
    timeout_timer.stop()
    _wait_for_idle(runner, qt_core_app)

    assert result == ["concluído"]
    assert worker_thread_ids[0] != threading.get_ident()
    assert progress_events == [(1, 1, "Etapa simulada")]


def test_cancellation_is_cooperative_and_stops_the_worker(
    qt_core_app, operation_runner: OperationRunner
) -> None:
    runner = operation_runner
    event_loop = QEventLoop()
    cancelled: list[str] = []
    runner.cancelled.connect(
        lambda operation_id: (cancelled.append(operation_id), event_loop.quit())
    )
    operation_id = runner.start(lambda token, _report: token.wait(5))
    cancel_timer = QTimer()
    cancel_timer.setSingleShot(True)
    cancel_timer.timeout.connect(lambda: runner.cancel(operation_id))
    cancel_timer.start(20)
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(event_loop.quit)
    timeout_timer.start(3000)
    event_loop.exec()
    cancel_timer.stop()
    timeout_timer.stop()
    _wait_for_idle(runner, qt_core_app)

    assert cancelled == [operation_id]
    assert runner.active_count == 0


def test_exception_details_are_reduced_to_safe_error_code(
    qt_core_app, operation_runner: OperationRunner
) -> None:
    runner = operation_runner
    event_loop = QEventLoop()
    error_codes: list[str] = []

    class UnsafeError(RuntimeError):
        code = "PASSWORD=nao-registrar"

    runner.failed.connect(lambda _operation_id, code: (error_codes.append(code), event_loop.quit()))
    runner.start(lambda _token, _report: (_ for _ in ()).throw(UnsafeError("segredo")))
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(event_loop.quit)
    timeout_timer.start(3000)
    event_loop.exec()
    timeout_timer.stop()
    _wait_for_idle(runner, qt_core_app)

    assert error_codes == ["OPERATION_FAILED"]

