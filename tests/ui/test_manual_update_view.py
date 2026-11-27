from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QListWidget, QPushButton

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.updates.preferences import SaveUpdatePreference
from manga_to_kindle.application.updates.refresh_manga_catalog import RefreshMangaCatalog
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.updates import UpdateCheck, UpdateCheckStatus
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.update_repository import UpdateRepository
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider

MANGA_ID = UUID("9a81f4e8-ad83-4a5b-a048-1f27e3bb3d4e")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _wait_until(app: QApplication, predicate, timeout_ms: int = 5000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    app.processEvents()
    assert predicate(), "A tela F010 não terminou de carregar no prazo."


def test_fixture_is_visible_as_demo_and_never_enables_manual_or_periodic_refresh(
    main_window,
    qt_core_app: QApplication,
    tmp_path,
) -> None:
    database = SQLiteDatabase(tmp_path / "updates-ui.sqlite3")
    database.initialize()
    provider = FixtureProvider()
    providers = ProviderRegistry((provider,))
    catalog = CatalogRepository(database)
    query = GetCatalog(providers)
    snapshot = RefreshCatalog(query, catalog).execute("https://fixture.invalid/manga/demo")
    repository = UpdateRepository(database)
    view = main_window.update_settings_view
    view.bind_services(
        repository,
        providers,
        SaveUpdatePreference(catalog, repository, providers),
        RefreshMangaCatalog(catalog, repository, providers),
    )
    try:
        _wait_until(qt_core_app, lambda: view.table.rowCount() == 1)
        row = view.table.cellWidget(0, 1)
        assert row is not None
        assert "Demonstração" in row.text()
        update_button = view.findChild(
            QPushButton,
            f"manualUpdate_{snapshot.manga.id}",
        )
        monitor_box = view.findChild(QCheckBox, f"monitorUpdates_{snapshot.manga.id}")
        assert update_button is not None and not update_button.isEnabled()
        assert monitor_box is not None and not monitor_box.isEnabled()
        assert not view._scheduler_timer.isActive()
        assert repository.get_preference(snapshot.manga.id).enabled is False
    finally:
        view.stop_scheduler()
        database.close()


def test_scheduler_timer_stops_when_application_closes(main_window) -> None:
    view = main_window.update_settings_view
    view._scheduler_timer.start(1000)
    assert view._scheduler_timer.isActive()
    view.stop_scheduler()
    assert not view._scheduler_timer.isActive()


def test_notice_dialog_displays_chapter_title_and_marks_only_selected_notices_read(
    main_window,
    qt_core_app: QApplication,
    tmp_path,
) -> None:
    database = SQLiteDatabase(tmp_path / "chapter-notices-ui.sqlite3")
    database.initialize()
    old_chapter = Chapter(
        manga_id=MANGA_ID,
        position=0,
        title="Capítulo 1",
        number=Decimal("1"),
        source_chapter_id="provider:chapter-1",
    )
    initial = CatalogSnapshot(
        provider_id="unregistered-provider",
        source_id="series:local",
        manga=Manga(
            id=MANGA_ID,
            title="Série local",
            source_ref="series:local",
            chapters=(old_chapter,),
        ),
        updated_at=NOW,
        simulated=False,
    )
    repository = UpdateRepository(database)
    repository.commit_snapshot(
        initial,
        UpdateCheck(
            manga_id=MANGA_ID,
            provider_id=initial.provider_id,
            started_at=NOW,
            finished_at=NOW,
            status=UpdateCheckStatus.SUCCEEDED,
            chapter_count=1,
        ),
        (),
    )
    new_chapter = Chapter(
        manga_id=MANGA_ID,
        id=uuid4(),
        position=1,
        title="Capítulo 2 — Um título novo",
        number=Decimal("2"),
        source_chapter_id="provider:chapter-2",
    )
    updated = CatalogSnapshot(
        provider_id=initial.provider_id,
        source_id=initial.source_id,
        manga=Manga(
            id=MANGA_ID,
            title=initial.manga.title,
            source_ref=initial.source_id,
            chapters=(old_chapter, new_chapter),
        ),
        updated_at=NOW + timedelta(minutes=1),
        simulated=False,
    )
    repository.commit_snapshot(
        updated,
        UpdateCheck(
            manga_id=MANGA_ID,
            provider_id=initial.provider_id,
            started_at=NOW + timedelta(minutes=1),
            finished_at=NOW + timedelta(minutes=1),
            status=UpdateCheckStatus.SUCCEEDED,
            chapter_count=2,
            new_chapter_count=1,
        ),
        ("provider:chapter-2",),
    )
    view = main_window.update_settings_view
    providers = ProviderRegistry(())
    view.bind_services(
        repository,
        providers,
        SaveUpdatePreference(CatalogRepository(database), repository, providers),
        RefreshMangaCatalog(CatalogRepository(database), repository, providers),
    )
    displayed_titles: list[str] = []

    def interact_with_dialog() -> None:
        dialog = qt_core_app.activeModalWidget()
        if isinstance(dialog, QDialog) and dialog.windowTitle().startswith("Novos capítulos"):
            notice_list = dialog.findChild(QListWidget)
            assert notice_list is not None
            displayed_titles.extend(
                notice_list.item(index).text() for index in range(notice_list.count())
            )
            mark_button = next(
                button
                for button in dialog.findChildren(QPushButton)
                if button.text() == "Marcar como lidos"
            )
            QTest.mouseClick(mark_button, Qt.MouseButton.LeftButton)
            return
        QTimer.singleShot(10, interact_with_dialog)

    try:
        _wait_until(qt_core_app, lambda: view.table.rowCount() == 1)
        button = view.findChild(QPushButton, f"readNotices_{MANGA_ID}")
        assert button is not None and button.isEnabled()
        QTimer.singleShot(0, interact_with_dialog)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        _wait_until(qt_core_app, lambda: repository.list_notices(MANGA_ID, unread_only=True) == ())
        assert any("Capítulo 2 — Um título novo" in title for title in displayed_titles)
    finally:
        view.stop_scheduler()
        deadline = time.monotonic() + 5
        while main_window.operation_runner.active_count and time.monotonic() < deadline:
            qt_core_app.processEvents()
            QTest.qWait(10)
        database.close()
