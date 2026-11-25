"""Fixtures reutilizáveis dos testes de widgets F002."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider
from manga_to_kindle.presentation.qt.main_window import MainWindow


@pytest.fixture
def main_window(qt_core_app: QApplication) -> Iterator[MainWindow]:
    query = GetCatalog(ProviderRegistry((FixtureProvider(),))).execute
    window = MainWindow(catalog_query=query)
    window.show()
    yield window
    window.operation_runner.cancel_all()
    if window.operation_runner.active_count:
        loop = QEventLoop()
        window.operation_runner.idle.connect(loop.quit)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
    window.allow_close()
    window.close()
    qt_core_app.processEvents()

