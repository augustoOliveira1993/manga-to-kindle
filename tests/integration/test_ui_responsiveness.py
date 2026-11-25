from __future__ import annotations

import socket
import time

from PySide6.QtCore import QEventLoop, QTimer

from manga_to_kindle.presentation.qt.main_window import MainWindow
from manga_to_kindle.presentation.qt.workers.demo import make_demo_operation


def test_thirty_second_simulation_keeps_navigation_and_cancel_responsive(
    qt_core_app, monkeypatch
) -> None:
    def reject_network(*_args, **_kwargs) -> None:
        raise AssertionError("F002 tentou acessar a rede")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    main_window = MainWindow()
    main_window.show()
    runner = main_window.operation_runner
    main_window.set_current_page("downloads")
    loop = QEventLoop()
    idle_loop = QEventLoop()
    event_times: list[float] = []
    cancelled: list[str] = []
    runner.cancelled.connect(
        lambda cancelled_operation: (
            cancelled.append(cancelled_operation),
            loop.quit(),
        )
    )
    started_at = time.perf_counter()
    operation_id = runner.start(make_demo_operation(total_steps=300, delay_seconds=0.1))

    def interact() -> None:
        event_times.append(time.perf_counter() - started_at)
        main_window.set_current_page("library")
        runner.cancel(operation_id)

    QTimer.singleShot(40, interact)
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    if runner.active_count:
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(3000, idle_loop.quit)
        idle_loop.exec()

    assert event_times and event_times[0] < 0.2
    assert main_window.page_title.text() == "Biblioteca"
    assert cancelled == [operation_id]
    assert runner.active_count == 0
    main_window.allow_close()
    main_window.close()
    qt_core_app.processEvents()

