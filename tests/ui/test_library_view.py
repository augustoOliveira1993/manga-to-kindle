from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from tests.library_support import seed_library

from manga_to_kindle.domain.library import LibraryAsset, LibraryEntry
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.models import (
    ImageImportJobRecord,
    MangaRecord,
    PageRecord,
    ProcessedPageRecord,
)
from manga_to_kindle.presentation.qt.views.library_view import (
    LibraryDeleteDialog,
    LibraryOrphanDeleteDialog,
)


def _wait_until(
    app: QApplication,
    predicate,
    timeout_ms: int = 5000,
    diagnostic: str = "",
) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    app.processEvents()
    assert predicate(), f"A operação da interface não terminou no prazo esperado. {diagnostic}"


def _add_managed_page(
    database: SQLiteDatabase,
    *,
    chapter_id,
    path: Path,
    payload: bytes,
    processed_path: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    page_id = uuid4()
    with database.unit_of_work() as session:
        session.add(
            PageRecord(
                id=page_id,
                chapter_id=chapter_id,
                position=0,
                original_path=str(path),
                source_sha256=hashlib.sha256(payload).hexdigest(),
                source_media_type="image/png",
            )
        )
        if processed_path is not None:
            processed_payload = payload + b"-processed"
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            processed_path.write_bytes(processed_payload)
            session.add(
                ProcessedPageRecord(
                    page_id=page_id,
                    output_order=0,
                    path=str(processed_path),
                    sha256=hashlib.sha256(processed_payload).hexdigest(),
                    width=600,
                    height=800,
                    profile_snapshot={},
                )
            )


def _accept_next_dialog(app: QApplication, *, select_first_asset: bool = False) -> None:
    deadline = time.monotonic() + 5

    def try_accept() -> None:
        dialog = app.activeModalWidget()
        if isinstance(dialog, (LibraryDeleteDialog, LibraryOrphanDeleteDialog)):
            if isinstance(dialog, LibraryDeleteDialog) and select_first_asset:
                first = next(iter(dialog.asset_checks.values()), None)
                if first is not None and first.isEnabled():
                    first.setChecked(True)
            dialog.accept()
            return
        if time.monotonic() < deadline:
            QTimer.singleShot(10, try_accept)

    QTimer.singleShot(0, try_accept)


def test_library_search_favorite_filter_and_history_use_persisted_records(
    main_window,
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    timestamp = datetime.now(UTC)
    with database.unit_of_work() as session:
        session.add(
            ImageImportJobRecord(
                id=uuid4(),
                source_kind="folder",
                source_fingerprint="a" * 64,
                target_manga_id=ids["Coração Azul"],
                target_chapter_id=ids["Coração Azul/1"],
                manga_title_snapshot="Coração Azul",
                chapter_title_snapshot="A chegada",
                state="failed",
                total_images=1,
                completed_images=0,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
    repository = LibraryRepository(database, (tmp_path / "managed",))
    view = main_window.library_view
    view.bind_services(repository)
    _wait_until(qt_core_app, lambda: view.results_list.count() > 0)

    view.search_input.setFocus()
    QTest.keyClicks(view.search_input, "CORACAO")
    _wait_until(
        qt_core_app,
        lambda: view.results_list.count() == 2
        and "Coração Azul" in view.results_list.item(0).text(),
    )
    first = view.results_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert isinstance(first, LibraryEntry)
    assert first.manga_id == ids["Coração Azul"]
    view.results_list.setCurrentRow(0)
    QTest.mouseClick(view.favorite_button, Qt.MouseButton.LeftButton)
    _wait_until(qt_core_app, lambda: "★ favorito" in view.results_list.item(0).text())

    view.search_input.clear()
    _wait_until(qt_core_app, lambda: view.results_list.count() == 4)
    view.favorite_filter.setChecked(True)
    _wait_until(qt_core_app, lambda: view.results_list.count() == 1)
    assert "★ favorito" in view.results_list.item(0).text()

    view.history_button.setChecked(True)
    _wait_until(qt_core_app, lambda: "histórico local" in view.state_label.text().lower())
    assert view.history_list.count() == 1
    history_text = view.history_list.item(0).text()
    assert "Coração Azul — A chegada" in history_text
    assert "Falhou" in history_text
    assert "início:" in history_text and "fim:" in history_text
    database.close()


def test_library_delete_dialog_cancellation_preserves_file_and_record(
    main_window,
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    payload = b"manual-confirmation-required"
    path = root / "page.png"
    _add_managed_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        path=path,
        payload=payload,
    )
    repository = LibraryRepository(database, (root,))
    view = main_window.library_view
    view.bind_services(repository)
    _wait_until(qt_core_app, lambda: view.results_list.count() > 0)
    target_row = next(
        row
        for row in range(view.results_list.count())
        if view.results_list.item(row).data(Qt.ItemDataRole.UserRole).manga_id
        == ids["Coração Azul"]
    )
    view.results_list.setCurrentRow(target_row)

    def reject_next_dialog() -> None:
        dialog = qt_core_app.activeModalWidget()
        if isinstance(dialog, QDialog):
            dialog.reject()
        else:
            QTimer.singleShot(10, reject_next_dialog)

    QTimer.singleShot(0, reject_next_dialog)
    QTest.mouseClick(view.delete_button, Qt.MouseButton.LeftButton)
    _wait_until(qt_core_app, lambda: "Remoção cancelada" in view.state_label.text())

    assert path.read_bytes() == payload
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is not None
    database.close()


def test_library_can_delete_one_confirmed_file_and_later_remove_orphan(
    main_window,
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    payload = b"confirmed-single-file"
    path = root / "original.png"
    processed_path = root / "processed.png"
    _add_managed_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        path=path,
        payload=payload,
        processed_path=processed_path,
    )
    repository = LibraryRepository(database, (root,))
    view = main_window.library_view
    view.bind_services(repository)
    _wait_until(qt_core_app, lambda: view.results_list.count() > 0)
    target_row = next(
        row
        for row in range(view.results_list.count())
        if view.results_list.item(row).data(Qt.ItemDataRole.UserRole).manga_id
        == ids["Coração Azul"]
    )
    view.results_list.setCurrentRow(target_row)
    assert view.delete_button.isEnabled()

    _accept_next_dialog(qt_core_app, select_first_asset=True)
    QTest.mouseClick(view.delete_button, Qt.MouseButton.LeftButton)
    _wait_until(
        qt_core_app,
        lambda: not path.exists(),
        timeout_ms=5000,
        diagnostic=f"estado={view.state_label.text()!r}; modal={qt_core_app.activeModalWidget()!r}",
    )
    _wait_until(qt_core_app, lambda: "Remoção concluída" in view.state_label.text())
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is None

    # The unselected processed file is represented as a separately deletable orphan.
    view.orphan_button.click()
    _wait_until(qt_core_app, lambda: view.results_list.count() == 1)
    orphan = view.results_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert isinstance(orphan, LibraryAsset)
    assert orphan.state.value == "unlinked"
    view.results_list.setCurrentRow(0)
    assert view.delete_button.isEnabled()
    _accept_next_dialog(qt_core_app)
    QTest.mouseClick(view.delete_button, Qt.MouseButton.LeftButton)
    _wait_until(qt_core_app, lambda: "Remoção concluída" in view.state_label.text())
    _wait_until(qt_core_app, lambda: not processed_path.exists())
    _wait_until(qt_core_app, lambda: view.results_list.count() == 0)
    database.close()
