"""Fixtures compartilhadas de teste."""

import os
from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_core_app() -> Iterator[QApplication]:
    """Cria uma aplicação Qt sem janela nativa para testes headless."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setOrganizationName("MangaToKindleTests")
    app.setApplicationName("MangaToKindleTests")
    yield app
