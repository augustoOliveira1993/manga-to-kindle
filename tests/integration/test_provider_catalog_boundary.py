from __future__ import annotations

import socket

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider
from manga_to_kindle.presentation.qt.main_window import MainWindow


def test_ui_resolves_only_fixture_provider_and_never_opens_network(
    qt_core_app: QApplication, monkeypatch
) -> None:
    def reject_network(*_args, **_kwargs) -> None:
        raise AssertionError("A fronteira fixture/UI não pode abrir sockets")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    query = GetCatalog(ProviderRegistry((FixtureProvider(),))).execute
    window = MainWindow(catalog_query=query)
    window.show()
    view = window.add_manga_view
    window.set_current_page("add")
    view.url_input.setText("https://example.test/manga")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait(window, qt_core_app)
    assert "não é suportada" in view.status_label.text().lower()
    assert view.chapter_list.count() == 0

    view.url_input.setText("https://fixture.invalid/manga/demo")
    QTest.mouseClick(view.query_button, Qt.MouseButton.LeftButton)
    _wait(window, qt_core_app)
    assert view.chapter_list.count() == 2
    assert "demonstração" in view.status_label.text().lower()
    window.allow_close()
    window.close()
    qt_core_app.processEvents()


def _wait(window: MainWindow, application: QApplication) -> None:
    loop = QEventLoop()
    operation_id = window.add_manga_view.operation_id
    window.operation_runner.finished.connect(
        lambda finished_id: loop.quit() if finished_id == operation_id else None
    )
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    application.processEvents()
    if window.operation_runner.active_count:
        idle_loop = QEventLoop()
        poll_timer = QTimer()
        poll_timer.setInterval(5)
        poll_timer.timeout.connect(
            lambda: idle_loop.quit()
            if window.operation_runner.active_count == 0
            else None
        )
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(idle_loop.quit)
        poll_timer.start()
        timeout_timer.start(3000)
        idle_loop.exec()
        poll_timer.stop()
        timeout_timer.stop()
        application.processEvents()
        assert window.operation_runner.active_count == 0
