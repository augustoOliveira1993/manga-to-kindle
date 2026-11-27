from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from manga_to_kindle.domain.settings import PAPERWHITE_10_PROFILE_ID
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.main import configure_application
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


def _wait_for_signal(signal, app: QApplication, timeout_ms: int = 5000) -> None:
    loop = QEventLoop()
    signal.connect(lambda *_args: loop.quit())
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    app.processEvents()


def _wait_for_idle(runner: OperationRunner, app: QApplication, timeout_ms: int = 5000) -> None:
    if not runner.active_count:
        app.processEvents()
        return
    loop = QEventLoop()
    runner.idle.connect(loop.quit)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    runner.idle.disconnect(loop.quit)
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
        "send",
        "settings",
        "images",
        "updates",
    }
    assert paths.database_file.is_file()
    assert "pronta" in window.startup_status.text().lower()
    assert controller.runtime is not None
    configure_application(window, controller.runtime)
    _wait_for_signal(window.settings_view.preferences_ready, qt_core_app)
    _wait_for_idle(window.operation_runner, qt_core_app)

    assert controller.runtime.database.current_revision() == "0011_mobi_export_artifacts"
    assert window.settings_view.profile_combo.count() == 3
    assert window.conversion_view.profile_combo.count() == 3
    assert window.conversion_view.output_path.text() == str(paths.data / "exports")
    assert window.downloads_view.refresh_button.isEnabled()
    paperwhite_index = window.settings_view.profile_combo.findData(PAPERWHITE_10_PROFILE_ID)
    window.settings_view.profile_combo.setCurrentIndex(paperwhite_index)
    window.settings_view.concurrency_spin.setValue(1)
    QTest.mouseClick(window.settings_view.save_profile_button, Qt.MouseButton.LeftButton)
    _wait_for_signal(window.settings_view.preferences_ready, qt_core_app)
    _wait_for_idle(window.operation_runner, qt_core_app)

    assert window.image_import_view.status_label.text().startswith(
        "Perfil ativo: Kindle Paperwhite"
    )
    assert window.conversion_view.profile_combo.currentData() == PAPERWHITE_10_PROFILE_ID
    assert controller.runtime is not None
    saved_preferences = window.settings_view._preferences
    assert saved_preferences is not None and saved_preferences.download_concurrency == 1

    window.set_current_page("add")
    window.add_manga_view.url_input.setText("https://fixture.invalid/manga/demo")
    window.add_manga_view.query_catalog()
    _wait_for_idle(window.operation_runner, qt_core_app)
    assert window.add_manga_view.status_label.text().startswith(
        "Catálogo de demonstração carregado"
    )

    window.set_current_page("updates")
    _wait_for_idle(window.operation_runner, qt_core_app)
    assert window.update_settings_view.table.rowCount() == 1
    source_status = window.update_settings_view.table.cellWidget(0, 1)
    assert source_status is not None
    assert "Demonstração; atualização bloqueada" in source_status.text()
    assert not window.update_settings_view._scheduler_timer.isActive()

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
