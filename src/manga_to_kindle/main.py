"""Ponto de entrada do aplicativo desktop."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
from manga_to_kindle.application.downloads.controls import (
    DownloadControls,
    DownloadControlSignals,
)
from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.infrastructure.config.settings import save_settings
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.image_import_repository import (
    ImageImportRepository,
)
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.os_open import DesktopSystemOpener
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow
from manga_to_kindle.application.transfers.open_manual_flow import OpenManualSend


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
        downloads = DownloadRepository(runtime.database, runtime.paths.data / "downloads")
        window.downloads_view.bind_queue(
            downloads,
            DownloadControls(downloads, DownloadControlSignals()),
            resume_available=False,
        )
        image_root = runtime.paths.data / "images"
        image_repository = ImageImportRepository(runtime.database, image_root)
        window.image_import_view.bind_services(
            ImportImages(
                LocalImageSourceReader(),
                PillowImageDecoder(),
                ImageStore(image_root),
                image_repository,
            ),
            image_repository,
        )
        export_repository = ExportRepository(runtime.database)
        window.conversion_view.bind_services(
            export_repository,
            CreateExport(
                export_repository,
                ExportOutputStore,
                NativeEpubWriter(),
                NativeCbzWriter(),
                ValidateEpub(),
                ValidateCbz(),
            ),
        )
        window.manual_send_view.bind_services(
            export_repository,
            OpenManualSend(export_repository, DesktopSystemOpener()),
        )
        def refresh_after_image_import(_result: object) -> None:
            window.conversion_view.refresh_chapters()
            window.library_view.refresh()

        window.image_import_view.import_finished.connect(refresh_after_image_import)
        window.library_view.bind_services(
            LibraryRepository(
                runtime.database,
                managed_roots=(
                    runtime.paths.data / "images",
                    runtime.paths.data / "downloads",
                ),
            )
        )
        window.operation_runner.succeeded.connect(
            lambda _operation_id, result: window.library_view.refresh()
            if isinstance(result, CatalogSnapshot)
            else None
        )

    controller.startup_finished.connect(configure_catalog_query)
    window.show()
    controller.start()
    return application.exec()
