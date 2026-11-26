from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from manga_to_kindle.domain.library import AvailabilityState, LibraryQuery
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.models import PageRecord
from tests.image_support import FIXTURES, make_image_stack, make_new_target


def test_imported_availability_reconciles_original_and_processed_files(
    tmp_path: Path,
) -> None:
    database, image_root, _store, _repo, _reader, _decoder, importer = make_image_stack(tmp_path)
    target = make_new_target("Coleção para biblioteca", "Capítulo local")
    plan = importer.preview_source(FIXTURES / "valid")
    importer.execute(plan, target, confirmed_authorization=True)
    repository = LibraryRepository(database, (image_root,))

    entry = next(
        item
        for item in repository.search(LibraryQuery(search_text="capitulo local")).entries
        if item.chapter_id == target.chapter_id
    )
    assert entry.availability is AvailabilityState.IMPORTED
    assert entry.page_count == 3

    with database.unit_of_work() as session:
        original_path = Path(
            session.scalar(
                select(PageRecord.original_path)
                .where(PageRecord.chapter_id == target.chapter_id)
                .order_by(PageRecord.position)
                .limit(1)
            )
        )
    original_path.unlink()
    missing = next(
        item
        for item in repository.search(LibraryQuery(search_text="capitulo local")).entries
        if item.chapter_id == target.chapter_id
    )
    assert missing.availability is AvailabilityState.MISSING
    assert missing.page_count == 3
    database.close()
