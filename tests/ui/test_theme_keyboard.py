from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from manga_to_kindle.infrastructure.config.settings import save_settings
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow


def _wait_for_signal(signal, qt_core_app: QApplication, timeout_ms: int = 5000) -> None:
    loop = QEventLoop()
    signal.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    qt_core_app.processEvents()


def _start_controller(
    qt_core_app: QApplication,
    root: Path,
) -> tuple[MainWindow, ApplicationController]:
    window = MainWindow()
    controller = ApplicationController(
        qt_core_app,
        window,
        AppPaths.from_root(root),
        settings_writer=save_settings,
    )
    controller.start()
    _wait_for_signal(controller.startup_finished, qt_core_app)
    assert controller.runtime is not None
    window.show()
    return window, controller


def _close_controller(
    window: MainWindow,
    controller: ApplicationController,
    app: QApplication,
) -> None:
    loop = QEventLoop()
    controller.shutdown_finished.connect(loop.quit)
    window.close()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    app.processEvents()
    assert controller.runtime is None
    window.deleteLater()
    controller.deleteLater()
    app.processEvents()


def test_theme_switch_is_keyboard_accessible_and_survives_two_restarts(
    qt_core_app: QApplication, tmp_path: Path
) -> None:
    window, controller = _start_controller(qt_core_app, tmp_path)
    window.set_current_page("settings")
    window.settings_view.dark_button.setFocus()
    QTest.keyClick(window.settings_view.dark_button, Qt.Key.Key_Space)
    _wait_for_signal(controller._operation_runner.idle, qt_core_app)
    assert controller.runtime is not None
    assert controller.runtime.settings.theme == "dark"
    assert window.theme == "dark"
    _close_controller(window, controller, qt_core_app)

    for _ in range(2):
        window, controller = _start_controller(qt_core_app, tmp_path)
        assert window.theme == "dark"
        assert window.settings_view.dark_button.isChecked()
        _close_controller(window, controller, qt_core_app)

