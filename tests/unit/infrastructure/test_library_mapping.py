from __future__ import annotations

from pathlib import Path

from tests.library_support import seed_library

from manga_to_kindle.domain.library import AvailabilityState, LibraryQuery
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository


def test_manga_without_chapters_maps_without_invented_metadata(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)

    result = LibraryRepository(database).search(
        LibraryQuery(search_text="manga sem capitulos")
    )

    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.manga_id == ids["Mangá sem capítulos"]
    assert entry.chapter_id is None
    assert entry.chapter_title is None
    assert entry.chapter_number is None
    assert entry.volume is None
    assert entry.author is None
    assert entry.availability is AvailabilityState.NOT_DOWNLOADED
    database.close()
