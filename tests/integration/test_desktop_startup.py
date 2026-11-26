from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow


def _wait_for_signal(signal, app: QApplication, timeout_ms: int = 5000) -> None:
    loop = QEventLoop()
    signal.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    app.processEvents()


def test_desktop_startup_composes_f001_runtime_and_f002_navigation(
    qt_core_app: QApplication, tmp_path: Path
) -> None:
    paths = AppPaths.from_root(tmp_path / "perfil local")
    window = MainWindow()
    controller = ApplicationController(qt_core_app, window, paths)
    controller.start()
    _wait_for_signal(controller.startup_finished, qt_core_app)

    assert controller.runtime is not None
    assert set(window.navigation_buttons) == {
        "library",
        "add",
        "downloads",
        "conversion",
        "settings",
        "images",
    }
    assert paths.database_file.is_file()
    assert "pronta" in window.startup_status.text().lower()

    loop = QEventLoop()
    controller.shutdown_finished.connect(loop.quit)
    window.close()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()

    assert controller.runtime is None
    assert paths.database_file.is_file()
    window.deleteLater()
    controller.deleteLater()
    qt_core_app.processEvents()
