from __future__ import annotations

import hashlib
from pathlib import Path

from manga_to_kindle.application.library.queries import SetLibraryFavorite
from manga_to_kindle.domain.library import AvailabilityState, LibraryQuery
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.models import PageRecord
from tests.library_support import seed_library


def test_library_state_and_search_survive_database_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "library.sqlite3"
    managed_root = tmp_path / "managed"
    page_path = managed_root / "page.png"
    page_path.parent.mkdir(parents=True)
    page_bytes = b"restart-page"
    page_path.write_bytes(page_bytes)
    database = SQLiteDatabase(database_path)
    database.initialize()
    ids = seed_library(database)
    with database.unit_of_work() as session:
        session.add(
            PageRecord(
                chapter_id=ids["Coração Azul/1"],
                position=0,
                original_path=str(page_path),
                source_sha256=hashlib.sha256(page_bytes).hexdigest(),
                source_media_type="image/png",
            )
        )
    repository = LibraryRepository(database, (managed_root,))
    SetLibraryFavorite(repository).execute(
        manga_id=ids["Coração Azul"],
        chapter_id=ids["Coração Azul/1"],
        favorite=True,
    )
    database.close()

    reopened = SQLiteDatabase(database_path)
    reopened.initialize()
    result = LibraryRepository(reopened, (managed_root,)).search(
        LibraryQuery(search_text="coracao", favorite_only=True)
    )

    assert len(result.entries) == 1
    assert result.entries[0].chapter_id == ids["Coração Azul/1"]
    assert result.entries[0].chapter_favorite
    assert result.entries[0].availability is AvailabilityState.PARTIAL
    assert result.entries[0].page_count == 1
    reopened.close()
