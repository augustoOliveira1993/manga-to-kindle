"""Ponto de entrada do aplicativo desktop."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.infrastructure.config.settings import save_settings
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow


def main(argv: Sequence[str] | None = None) -> int:
    application = QApplication(list(argv) if argv is not None else sys.argv)
    application.setOrganizationName("MangaToKindle")
    application.setApplicationName("MangaToKindle")
    window = MainWindow()
    controller = ApplicationController(application, window, settings_writer=save_settings)

    def configure_catalog_query() -> None:
        runtime = controller.runtime
        if runtime is None or runtime.closed:
            return
        query = GetCatalog(ProviderRegistry((FixtureProvider(),)))
        refresh = RefreshCatalog(query, CatalogRepository(runtime.database))
        window.add_manga_view.set_catalog_query(refresh.execute)

    controller.startup_finished.connect(configure_catalog_query)
    window.show()
    controller.start()
    return application.exec()
