"""Composition root da fundação local."""

from __future__ import annotations

from manga_to_kindle.application.downloads.recovery import DownloadRecovery
from manga_to_kindle.application.errors import describe_startup_error
from manga_to_kindle.application.images.recovery import RecoverImageImports
from manga_to_kindle.application.lifecycle import ApplicationRuntime
from manga_to_kindle.infrastructure.config.settings import AppSettings, load_or_create_settings
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.logging import configure_logging
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.download_repository import (
    DownloadRepository,
)
from manga_to_kindle.infrastructure.persistence.image_import_repository import (
    ImageImportRepository,
)
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository


def bootstrap_application(paths: AppPaths | None = None) -> ApplicationRuntime:
    """Prepara filesystem, config, logs e SQLite antes de habilitar a interface."""
    resolved_paths = paths or AppPaths.from_qstandardpaths()
    resolved_paths.ensure()

    default_settings = AppSettings()
    logging_manager = configure_logging(resolved_paths.log_file, default_settings)
    database: SQLiteDatabase | None = None
    try:
        settings = load_or_create_settings(resolved_paths)
        logging_manager.configure(resolved_paths.log_file, settings)
        database = SQLiteDatabase(resolved_paths.database_file)
        database.initialize()
        download_root = resolved_paths.data / "downloads"
        DownloadRecovery(
            DownloadRepository(database, download_root),
            PageStore(download_root),
        ).execute()
        image_root = resolved_paths.data / "images"
        RecoverImageImports(
            ImageImportRepository(database, image_root),
            ImageStore(image_root),
        ).execute()
        LibraryRepository(
            database,
            managed_roots=(image_root, download_root),
        ).recover_deletions()
        logging_manager.logger.info("application startup complete")
        return ApplicationRuntime(
            paths=resolved_paths,
            settings=settings,
            logging=logging_manager,
            database=database,
        )
    except Exception as exc:
        error_info = describe_startup_error(exc)
        logging_manager.logger.error(
            "application startup failed code=%s exception_type=%s fields=%s",
            error_info.code,
            type(exc).__name__,
            getattr(exc, "fields", ()),
        )
        if database is not None:
            try:
                database.close()
            except Exception:
                pass
        logging_manager.close()
        raise
