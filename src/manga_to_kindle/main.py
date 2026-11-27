"""Ponto de entrada do aplicativo desktop."""

from __future__ import annotations

import socket
import sys
from collections.abc import Sequence
from uuid import UUID

from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
from manga_to_kindle.application.downloads.controls import (
    DownloadControls,
    DownloadControlSignals,
)
from manga_to_kindle.application.downloads.enqueue import EnqueueDownload, PreparedDownload
from manga_to_kindle.application.downloads.queue import DownloadQueue
from manga_to_kindle.application.downloads.restore_references import RestoreDownloadReferences
from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.application.lifecycle import ApplicationRuntime
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.settings.cache import (
    ClearRegenerableCache,
    PreviewCacheCleanup,
)
from manga_to_kindle.application.settings.device_profiles import (
    ListDeviceProfiles,
    RemoveDeviceProfile,
    SaveDeviceProfile,
)
from manga_to_kindle.application.settings.preferences import (
    GetApplicationPreferences,
    ResetPreferences,
    SaveApplicationPreferences,
)
from manga_to_kindle.application.transfers.open_manual_flow import OpenManualSend
from manga_to_kindle.application.transfers.ports import VaultUnavailable
from manga_to_kindle.application.transfers.smtp_send import (
    PreviewSmtpTransfer,
    SendSmtpTransfer,
)
from manga_to_kindle.application.transfers.smtp_settings import (
    RemoveSmtpProfile,
    SaveSmtpProfile,
    TestSmtpConnection,
)
from manga_to_kindle.application.updates.preferences import SaveUpdatePreference
from manga_to_kindle.application.updates.refresh_manga_catalog import RefreshMangaCatalog
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.settings import ApplicationPreferences, DeviceProfileSettings
from manga_to_kindle.infrastructure.config.settings import save_settings
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.kcc_adapter import create_kcc_writer
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader
from manga_to_kindle.infrastructure.network.pinned_http_transport import PinnedHttpTransport
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.os_open import DesktopSystemOpener
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.image_import_repository import (
    ImageImportRepository,
)
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.settings_repository import SettingsRepository
from manga_to_kindle.infrastructure.persistence.transfer_repository import TransferRepository
from manga_to_kindle.infrastructure.persistence.update_repository import UpdateRepository
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider
from manga_to_kindle.infrastructure.providers.ndl_provider import NdlProvider
from manga_to_kindle.infrastructure.security.credential_vault import WindowsCredentialVault
from manga_to_kindle.infrastructure.transfers.smtp_transport import SmtpTransport
from manga_to_kindle.presentation.qt.lifecycle import ApplicationController
from manga_to_kindle.presentation.qt.main_window import MainWindow


def _resolve_external_host(host: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            address
            for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            if isinstance((address := result[4][0]), str)
        )
    )


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
        configure_application(window, runtime)

    controller.startup_finished.connect(configure_catalog_query)
    window.show()
    controller.start()
    return application.exec()


def configure_application(window: MainWindow, runtime: ApplicationRuntime) -> None:
    """Inject local services after startup and connect persisted preferences to consumers."""
    url_policy = ExternalUrlPolicy(_resolve_external_host)
    network_transport = PinnedHttpTransport(url_policy)
    providers = ProviderRegistry(
        (
            FixtureProvider(),
            NdlProvider(network_transport, url_policy),
        )
    )
    query = GetCatalog(providers)
    catalog_repository = CatalogRepository(runtime.database)
    refresh = RefreshCatalog(query, catalog_repository)
    window.add_manga_view.set_catalog_query(refresh.execute)
    update_repository = UpdateRepository(runtime.database)
    window.update_settings_view.bind_services(
        update_repository,
        providers,
        SaveUpdatePreference(catalog_repository, update_repository, providers),
        RefreshMangaCatalog(catalog_repository, update_repository, providers),
    )

    def refresh_updates_page(page: str) -> None:
        if page == "updates":
            window.update_settings_view.refresh()

    window.page_changed.connect(refresh_updates_page)
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
            create_kcc_writer,
        ),
    )
    window.manual_send_view.bind_services(
        export_repository,
        OpenManualSend(export_repository, DesktopSystemOpener()),
    )
    transfer_repository = TransferRepository(runtime.database)
    try:
        credential_vault = WindowsCredentialVault()
    except VaultUnavailable:
        window.manual_send_view.history_view.bind_repository(transfer_repository)
        window.manual_send_view.disable_smtp()
    else:
        smtp_transport = SmtpTransport()
        window.manual_send_view.bind_smtp_services(
            transfer_repository,
            SaveSmtpProfile(transfer_repository, credential_vault),
            RemoveSmtpProfile(transfer_repository, credential_vault),
            TestSmtpConnection(transfer_repository, credential_vault, smtp_transport),
            PreviewSmtpTransfer(export_repository, transfer_repository, transfer_repository),
            SendSmtpTransfer(
                export_repository,
                transfer_repository,
                transfer_repository,
                credential_vault,
                smtp_transport,
            ),
        )

    def refresh_after_image_import(_result: object) -> None:
        window.conversion_view.refresh_chapters()
        window.library_view.refresh()

    window.image_import_view.import_finished.connect(refresh_after_image_import)
    window.library_view.bind_services(
        LibraryRepository(
            runtime.database,
            managed_roots=(image_root, runtime.paths.data / "downloads"),
        )
    )
    window.operation_runner.succeeded.connect(
        lambda _operation_id, result: (
            window.library_view.refresh() if isinstance(result, CatalogSnapshot) else None
        )
    )

    settings_repository = SettingsRepository(runtime.database)
    window.settings_view.bind_services(
        GetApplicationPreferences(settings_repository, runtime.paths),
        ListDeviceProfiles(settings_repository),
        SaveDeviceProfile(settings_repository),
        RemoveDeviceProfile(settings_repository, settings_repository),
        SaveApplicationPreferences(settings_repository, profile_lookup=settings_repository),
        ResetPreferences(settings_repository, runtime.paths),
        PreviewCacheCleanup(settings_repository),
        ClearRegenerableCache(settings_repository),
    )

    def apply_preferences(preferences_value: object, profiles_value: object) -> None:
        if not isinstance(preferences_value, ApplicationPreferences):
            return
        if not isinstance(profiles_value, tuple) or not all(
            isinstance(profile, DeviceProfileSettings) for profile in profiles_value
        ):
            return
        preferences = preferences_value
        profiles = profiles_value
        selected = next(
            (profile for profile in profiles if profile.id == preferences.selected_profile_id),
            None,
        )
        if selected is None:
            return
        window.image_import_view.set_device_profile(selected)
        window.conversion_view.set_device_profiles(profiles, selected.id)
        if preferences.export_directory is not None:
            window.conversion_view.set_default_output_directory(preferences.export_directory)
        if preferences.download_directory is not None:
            downloads = DownloadRepository(runtime.database, preferences.download_directory)
            download_signals = DownloadControlSignals()
            download_queue = DownloadQueue(
                downloads,
                network_transport,
                PageStore(preferences.download_directory),
                url_policy,
                download_signals,
            )
            enqueuer = EnqueueDownload(downloads, url_policy)

            def prepare_download(
                catalog: CatalogSnapshot,
                selected_chapter_ids: tuple[UUID, ...],
            ) -> PreparedDownload:
                provider = providers.by_id(catalog.provider_id)
                return enqueuer.prepare(
                    provider=provider,
                    catalog=catalog,
                    selected_chapter_ids=selected_chapter_ids,
                )

            window.add_manga_view.set_download_preparer(prepare_download)
            window.add_manga_view.download_enqueued.connect(
                window.downloads_view.start_download
            )
            window.downloads_view.bind_queue(
                downloads,
                DownloadControls(downloads, download_signals),
                download_queue=download_queue,
                resume_preparer=RestoreDownloadReferences(downloads, providers).execute,
            )
            window.library_view.bind_services(
                LibraryRepository(
                    runtime.database,
                    managed_roots=(image_root, preferences.download_directory),
                )
            )

    window.settings_view.preferences_ready.connect(apply_preferences)


if __name__ == "__main__":
    raise SystemExit(main())
