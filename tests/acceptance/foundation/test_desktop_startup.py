from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow


def test_window_stays_responsive_while_local_bootstrap_runs(
    qt_core_app: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import manga_to_kindle.presentation.qt.startup as startup_module

    original_bootstrap = startup_module.bootstrap_application
    worker_thread_ids: list[int] = []

    def delayed_bootstrap(paths: AppPaths):
        worker_thread_ids.append(threading.get_ident())
        time.sleep(0.1)
        return original_bootstrap(paths)

    monkeypatch.setattr(startup_module, "bootstrap_application", delayed_bootstrap)
    monkeypatch.setattr(QMessageBox, "critical", lambda *_args: QMessageBox.StandardButton.Ok)
    window = MainWindow()
    controller = ApplicationController(qt_core_app, window, AppPaths.from_root(tmp_path))
    loop = QEventLoop()
    timer_fired: list[bool] = []
    QTimer.singleShot(10, lambda: timer_fired.append(True))
    controller.startup_finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)

    window.show()
    controller.start()
    loop.exec()

    assert controller.runtime is not None, window.findChild(QLabel, "startupStatus").text()  # type: ignore[union-attr]
    assert timer_fired == [True]
    assert worker_thread_ids
    assert worker_thread_ids[0] != threading.get_ident()
    status_label = window.findChild(QLabel, "startupStatus")
    assert status_label is not None
    assert "pronta" in status_label.text().lower()

    shutdown_loop = QEventLoop()
    controller.shutdown_finished.connect(shutdown_loop.quit)
    window.close()
    QTimer.singleShot(5000, shutdown_loop.quit)
    shutdown_loop.exec()

    assert controller.runtime is None, status_label.text()
