from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import insert

from manga_to_kindle.application.library.queries import QueryLibrary, SetLibraryFavorite
from manga_to_kindle.domain.library import (
    ActivityKind,
    AvailabilityState,
    LibraryPreferences,
    LibraryQuery,
    LibrarySort,
    normalize_search_text,
)
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.models import ChapterRecord, MangaRecord
from tests.library_support import seed_library


def test_library_search_ignores_case_and_accents_and_orders_stably(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    query = QueryLibrary(LibraryRepository(database))

    by_title = query.execute(LibraryQuery(search_text="  CORACAO "))
    by_author = query.execute(LibraryQuery(search_text="agata nogueira"))
    by_chapter = query.execute(LibraryQuery(search_text="CAFÉ"))
    by_number = query.execute(LibraryQuery(search_text="2.5"))
    first_order = query.execute(LibraryQuery(sort=LibrarySort.TITLE))
    second_order = query.execute(LibraryQuery(sort=LibrarySort.TITLE))

    assert {entry.manga_id for entry in by_title.entries} == {ids["Coração Azul"]}
    assert {entry.manga_id for entry in by_author.entries} == {ids["Coração Azul"]}
    assert len(by_chapter.entries) == 1
    assert by_chapter.entries[0].chapter_title == "Especial: Café"
    assert by_number.entries[0].chapter_id == ids["Coração Azul/2.5"]
    assert [entry.chapter_id for entry in first_order.entries] == [
        entry.chapter_id for entry in second_order.entries
    ]
    assert first_order.total == 4
    database.close()


def test_favorites_and_filters_persist_without_affecting_catalog_records(tmp_path: Path) -> None:
    database_path = tmp_path / "library.sqlite3"
    database = SQLiteDatabase(database_path)
    database.initialize()
    ids = seed_library(database)
    repository = LibraryRepository(database)
    SetLibraryFavorite(repository).execute(
        manga_id=ids["Coração Azul"],
        chapter_id=None,
        favorite=True,
    )
    SetLibraryFavorite(repository).execute(
        manga_id=ids["Cidade de Papel"],
        chapter_id=ids["Cidade de Papel/1"],
        favorite=True,
    )
    saved = LibraryPreferences(
        favorite_only=True,
        availability=AvailabilityState.IMPORTED,
        download_state="paused",
        export_state="completed",
        sort=LibrarySort.CHAPTER,
    )
    repository.save_preferences(saved)
    favorites = repository.search(LibraryQuery(favorite_only=True))
    database.close()

    reopened = SQLiteDatabase(database_path)
    reopened.initialize()
    reopened_repository = LibraryRepository(reopened)
    persisted_favorites = reopened_repository.search(LibraryQuery(favorite_only=True))
    with reopened.unit_of_work() as session:
        unchanged = session.get(MangaRecord, ids["Coração Azul"])

    assert {entry.manga_id for entry in favorites.entries} == {
        ids["Coração Azul"],
        ids["Cidade de Papel"],
    }
    assert persisted_favorites == favorites
    assert unchanged is not None and unchanged.provider_id == "library-demo"
    assert unchanged.source_ref == f"library-demo:{ids['Coração Azul']}"
    assert reopened_repository.get_preferences() == saved
    reopened.close()


def test_availability_distinguishes_download_import_missing_and_altered_files(
    tmp_path: Path,
) -> None:
    from hashlib import sha256

    from manga_to_kindle.infrastructure.persistence.models import (
        DownloadChapterRecord,
        DownloadJobRecord,
        DownloadPageRecord,
        ImageImportJobRecord,
        PageRecord,
        ProcessedPageRecord,
    )

    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    imported_id = ids["Coração Azul/1"]
    downloaded_id = ids["Coração Azul/2.5"]
    partial_id = ids["Cidade de Papel/1"]
    original_bytes = b"synthetic-original"
    derived_bytes = b"synthetic-derived"
    original_path = tmp_path / "images" / "original.bin"
    derived_path = tmp_path / "images" / "derived.bin"
    downloaded_path = tmp_path / "downloads" / "page.bin"
    partial_path = tmp_path / "images" / "partial.bin"
    for path, data in (
        (original_path, original_bytes),
        (derived_path, derived_bytes),
        (downloaded_path, original_bytes),
        (partial_path, original_bytes),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    now = datetime.now(UTC)
    import_job_id, download_job_id = uuid4(), uuid4()
    imported_page_id = uuid4()
    downloaded_page_id = uuid4()
    with database.unit_of_work() as session:
        session.add(
            ImageImportJobRecord(
                id=import_job_id,
                source_kind="folder",
                source_fingerprint="1" * 64,
                target_manga_id=ids["Coração Azul"],
                target_chapter_id=imported_id,
                state="succeeded",
                total_images=1,
                completed_images=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            PageRecord(
                id=imported_page_id,
                chapter_id=imported_id,
                position=0,
                original_path=str(original_path),
                source_sha256=sha256(original_bytes).hexdigest(),
                import_job_id=import_job_id,
            )
        )
        session.add(
            ProcessedPageRecord(
                id=uuid4(),
                page_id=imported_page_id,
                output_order=0,
                path=str(derived_path),
                sha256=sha256(derived_bytes).hexdigest(),
                width=600,
                height=800,
                profile_snapshot={},
                created_at=now,
            )
        )
        session.add(
            DownloadJobRecord(
                id=download_job_id,
                chapter_id=downloaded_id,
                manga_id=None,
                state="succeeded",
                progress=1,
                total=1,
                cancel_requested=False,
                provider_id="authorized-test",
                policy_snapshot={},
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            DownloadChapterRecord(
                job_id=download_job_id,
                chapter_id=downloaded_id,
                position=0,
                state="complete",
                page_total=1,
                page_completed=1,
            )
        )
        session.add(
            DownloadPageRecord(
                id=downloaded_page_id,
                job_id=download_job_id,
                chapter_id=downloaded_id,
                provider_id="authorized-test",
                provider_page_id="page-1",
                position=0,
                state="complete",
                attempts=1,
                byte_size=len(original_bytes),
                sha256=sha256(original_bytes).hexdigest(),
                original_path=str(downloaded_path),
                duplicate_content=False,
            )
        )
        session.add(
            PageRecord(
                id=downloaded_page_id,
                chapter_id=downloaded_id,
                position=0,
                original_path=str(downloaded_path),
            )
        )
        session.add(
            PageRecord(
                id=uuid4(),
                chapter_id=partial_id,
                position=0,
                original_path=str(partial_path),
            )
        )

    repository = LibraryRepository(database)
    entries = {
        entry.chapter_id: entry
        for entry in repository.search(LibraryQuery(limit=50)).entries
        if entry.chapter_id is not None
    }
    assert entries[imported_id].availability is AvailabilityState.IMPORTED
    assert entries[downloaded_id].availability is AvailabilityState.DOWNLOADED
    assert entries[partial_id].availability is AvailabilityState.PARTIAL
    assert entries[ids["Cidade de Papel/1"]].page_count == 1
    downloaded_filter = repository.search(LibraryQuery(download_state="succeeded"))
    assert {entry.chapter_id for entry in downloaded_filter.entries} == {downloaded_id}
    assert any(
        entry.availability is AvailabilityState.NOT_DOWNLOADED
        for entry in repository.search(
            LibraryQuery(availability=AvailabilityState.NOT_DOWNLOADED)
        ).entries
    )
    downloaded_path.unlink()
    changed_path = tmp_path / "images" / "changed.bin"
    changed_path.write_bytes(b"wrong bytes")
    with database.unit_of_work() as session:
        session.add(
            PageRecord(
                id=uuid4(),
                chapter_id=ids["Cidade de Papel/1"],
                position=1,
                original_path=str(changed_path),
                source_sha256=sha256(original_bytes).hexdigest(),
            )
        )
    after_changes = {
        entry.chapter_id: entry
        for entry in repository.search(LibraryQuery(limit=50)).entries
        if entry.chapter_id is not None
    }
    assert after_changes[downloaded_id].availability is AvailabilityState.MISSING
    assert after_changes[partial_id].availability is AvailabilityState.ALTERED
    database.close()


def test_history_unifies_download_import_and_export_records_without_absolute_paths(
    tmp_path: Path,
) -> None:
    from manga_to_kindle.infrastructure.persistence.models import (
        DownloadJobRecord,
        ExportRecord,
        ImageImportJobRecord,
    )

    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    now = datetime.now(UTC)
    with database.unit_of_work() as session:
        session.add(
            DownloadJobRecord(
                id=uuid4(),
                manga_id=ids["Coração Azul"],
                chapter_id=None,
                state="failed",
                progress=0,
                total=1,
                cancel_requested=False,
                provider_id="fixture",
                policy_snapshot={},
                error_code="SOURCE_UNAUTHORIZED",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ImageImportJobRecord(
                id=uuid4(),
                source_kind="folder",
                source_fingerprint="2" * 64,
                target_manga_id=ids["Coração Azul"],
                target_chapter_id=ids["Coração Azul/1"],
                state="failed",
                total_images=1,
                completed_images=0,
                error_code="IMPORT_CANCELLED",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ExportRecord(
                id=uuid4(),
                profile_snapshot={"format": "epub"},
                destination=str(tmp_path / "outputs"),
                state="completed",
                created_at=now,
                updated_at=now,
            )
        )

    history = LibraryRepository(database).history()

    assert {item.kind for item in history} == {
        ActivityKind.DOWNLOAD,
        ActivityKind.IMAGE_IMPORT,
        ActivityKind.EXPORT,
    }
    assert {item.reason_code for item in history} == {
        "SOURCE_UNAUTHORIZED",
        "IMPORT_CANCELLED",
        None,
    }
    assert all(not Path(item.location_name or "").is_absolute() for item in history)
    export_activity = next(item for item in history if item.kind is ActivityKind.EXPORT)
    assert export_activity.identity == "0 capítulos"
    database.close()


def test_search_returns_first_page_under_half_second_for_110000_records(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    now = datetime.now(UTC)
    manga_ids = [uuid4() for _ in range(10_000)]
    with database.unit_of_work() as session:
        session.execute(
            insert(MangaRecord),
            [
                {
                    "id": manga_id,
                    "title": f"Manga {index:05d}",
                    "search_key": normalize_search_text(f"Manga {index:05d}"),
                    "simulated": False,
                    "favorite": False,
                    "created_at": now,
                    "updated_at": now,
                }
                for index, manga_id in enumerate(manga_ids)
            ],
        )
        session.execute(
            insert(ChapterRecord),
            [
                {
                    "id": uuid4(),
                    "manga_id": manga_id,
                    "title": f"Capítulo {position}",
                    "search_key": normalize_search_text(
                        f"Capítulo {position} {position}"
                    ),
                    "number": str(position),
                    "position": position,
                    "favorite": False,
                    "created_at": now,
                }
                for manga_id in manga_ids
                for position in range(10)
            ],
        )
    repository = LibraryRepository(database)
    started = time.perf_counter()
    page = repository.search(LibraryQuery(search_text="manga", limit=100))
    elapsed = time.perf_counter() - started

    assert page.total == 100_000
    assert len(page.entries) == 100
    assert elapsed < 0.5
    database.close()
