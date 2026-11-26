from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from tests.library_support import seed_library

from manga_to_kindle.domain.library import LibraryAssetState
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import (
    LibraryPersistenceError,
    LibraryRepository,
)
from manga_to_kindle.infrastructure.persistence.models import (
    ChapterRecord,
    LibraryAssetRecord,
    LibraryDeletionItemRecord,
    LibraryDeletionPlanRecord,
    MangaRecord,
    PageRecord,
    ProcessedPageRecord,
)


def _add_page(
    database: SQLiteDatabase,
    *,
    chapter_id,
    original_path: Path,
    processed_path: Path,
    original_bytes: bytes,
    processed_bytes: bytes,
) -> None:
    original_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(original_bytes)
    processed_path.write_bytes(processed_bytes)
    page_id = uuid4()
    with database.unit_of_work() as session:
        session.add(
            PageRecord(
                id=page_id,
                chapter_id=chapter_id,
                position=0,
                original_path=str(original_path),
                source_sha256=hashlib.sha256(original_bytes).hexdigest(),
                source_media_type="image/png",
            )
        )
        session.add(
            ProcessedPageRecord(
                page_id=page_id,
                output_order=0,
                path=str(processed_path),
                sha256=hashlib.sha256(processed_bytes).hexdigest(),
                width=600,
                height=800,
                profile_snapshot={},
            )
        )


def test_cancelled_confirmation_does_not_change_records_files_or_create_plan(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    repository = LibraryRepository(database, (tmp_path / "managed",))
    preview = repository.preview_delete(ids["Coração Azul"])
    with database.unit_of_work() as session:
        before_count = len(tuple(session.scalars(select(MangaRecord.id))))

    with pytest.raises(LibraryPersistenceError, match="confirmação explícita"):
        repository.delete_scope(preview, asset_ids=(), confirmed=False)

    with database.unit_of_work() as session:
        after_count = len(tuple(session.scalars(select(MangaRecord.id))))
        plan_count = len(tuple(session.scalars(select(LibraryDeletionPlanRecord.id))))
    assert before_count == after_count
    assert plan_count == 0
    database.close()


def test_record_only_removal_preserves_files_as_individually_tracked_orphans(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    original = b"managed-original"
    processed = b"managed-processed"
    original_path = root / "originals" / "page.png"
    processed_path = root / "processed" / "page.png"
    _add_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        original_path=original_path,
        processed_path=processed_path,
        original_bytes=original,
        processed_bytes=processed,
    )
    repository = LibraryRepository(database, (root,))
    preview = repository.preview_delete(ids["Coração Azul"])

    result = repository.delete_scope(preview, asset_ids=(), confirmed=True)

    assert result.state == "completed"
    assert result.removed_record_count > 0
    assert result.removed_file_count == 0
    assert original_path.read_bytes() == original
    assert processed_path.read_bytes() == processed
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is None
        assert session.get(ChapterRecord, ids["Coração Azul/1"]) is None
        tracked = tuple(session.scalars(select(LibraryAssetRecord)))
    assert {Path(item.path) for item in tracked} == {original_path, processed_path}
    assert all(item.state == "unlinked" and item.managed for item in tracked)
    database.close()


def test_confirmed_asset_selection_removes_only_selected_file_and_keeps_other_bytes(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    first = b"selected-file"
    second = b"kept-file"
    first_path = root / "first.png"
    second_path = root / "second.png"
    _add_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        original_path=first_path,
        processed_path=root / "processed-first.png",
        original_bytes=first,
        processed_bytes=b"processed-first",
    )
    _add_page(
        database,
        chapter_id=ids["Coração Azul/2.5"],
        original_path=second_path,
        processed_path=root / "processed-second.png",
        original_bytes=second,
        processed_bytes=b"processed-second",
    )
    repository = LibraryRepository(database, (root,))
    preview = repository.preview_delete(ids["Coração Azul"])
    selected_id = next(item.id for item in preview.assets if item.path == first_path)

    result = repository.delete_scope(preview, asset_ids=(selected_id,), confirmed=True)

    assert result.state == "completed"
    assert result.removed_file_count == 1
    assert not first_path.exists()
    assert second_path.read_bytes() == second
    orphans = repository.list_unlinked_assets()
    assert any(
        item.path == second_path and item.state is LibraryAssetState.UNLINKED
        for item in orphans
    )
    assert any(
        item.path == root / "processed-first.png" and item.state is LibraryAssetState.UNLINKED
        for item in orphans
    )
    database.close()


def test_altered_file_is_preserved_and_reported_without_blocking_record_removal(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    original_path = root / "original.png"
    _add_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        original_path=original_path,
        processed_path=root / "processed.png",
        original_bytes=b"expected-original",
        processed_bytes=b"processed",
    )
    original_path.write_bytes(b"changed-after-import")
    repository = LibraryRepository(database, (root,))
    preview = repository.preview_delete(ids["Coração Azul"])
    changed_asset = next(item for item in preview.assets if item.path == original_path)

    result = repository.delete_scope(
        preview,
        asset_ids=(changed_asset.id,),
        confirmed=True,
    )

    assert result.state == "partial"
    assert result.error_code == "ASSET_DELETE_INCOMPLETE"
    assert original_path.read_bytes() == b"changed-after-import"
    assert any(
        item.path == original_path and item.state is LibraryAssetState.CHANGED
        for item in repository.list_unlinked_assets()
    )
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is None
    database.close()


def test_external_original_cannot_be_selected_for_deletion(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    external_root = tmp_path / "external-source"
    external_root.mkdir()
    original_path = external_root / "source.png"
    original_path.write_bytes(b"external-source")
    with database.unit_of_work() as session:
        session.add(
            PageRecord(
                chapter_id=ids["Coração Azul/1"],
                position=0,
                original_path=str(original_path),
                source_sha256=hashlib.sha256(b"external-source").hexdigest(),
                source_media_type="image/png",
            )
        )
    repository = LibraryRepository(database, (tmp_path / "managed",))
    preview = repository.preview_delete(ids["Coração Azul"])
    external_asset = next(item for item in preview.assets if item.path == original_path)

    assert external_asset.managed is False
    with pytest.raises(LibraryPersistenceError, match="cópias gerenciadas"):
        repository.delete_scope(
            preview,
            asset_ids=(external_asset.id,),
            confirmed=True,
        )
    assert original_path.read_bytes() == b"external-source"
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is not None
    database.close()


def test_unlinked_asset_can_be_deleted_later_after_separate_confirmation(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    original_path = root / "original.png"
    _add_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        original_path=original_path,
        processed_path=root / "processed.png",
        original_bytes=b"original",
        processed_bytes=b"processed",
    )
    repository = LibraryRepository(database, (root,))
    preview = repository.preview_delete(ids["Coração Azul"])
    repository.delete_scope(preview, asset_ids=(), confirmed=True)
    orphan = next(item for item in repository.list_unlinked_assets() if item.path == original_path)

    result = repository.delete_unlinked_assets((orphan.id,), confirmed=True)

    assert result.state == "completed"
    assert result.removed_file_count == 1
    assert not original_path.exists()
    assert all(item.path != original_path for item in repository.list_unlinked_assets())
    database.close()


def test_shared_page_path_is_protected_from_a_manga_scope_delete(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    ids = seed_library(database)
    root = tmp_path / "managed"
    shared = root / "shared.png"
    payload = b"shared-between-manga"
    _add_page(
        database,
        chapter_id=ids["Coração Azul/1"],
        original_path=shared,
        processed_path=root / "processed-a.png",
        original_bytes=payload,
        processed_bytes=b"processed-a",
    )
    _add_page(
        database,
        chapter_id=ids["Cidade de Papel/1"],
        original_path=shared,
        processed_path=root / "processed-b.png",
        original_bytes=payload,
        processed_bytes=b"processed-b",
    )
    repository = LibraryRepository(database, (root,))
    preview = repository.preview_delete(ids["Coração Azul"])
    shared_asset = next(item for item in preview.assets if item.path == shared)

    assert shared_asset.shared
    with pytest.raises(LibraryPersistenceError, match="compartilhado"):
        repository.delete_scope(
            preview,
            asset_ids=(shared_asset.id,),
            confirmed=True,
        )
    assert shared.read_bytes() == payload
    with database.unit_of_work() as session:
        assert session.get(MangaRecord, ids["Coração Azul"]) is not None
        assert session.get(MangaRecord, ids["Cidade de Papel"]) is not None
    database.close()


def test_interrupted_deletion_plan_is_reconciled_without_widening_scope(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    root = tmp_path / "managed"
    path = root / "kept.png"
    path.parent.mkdir(parents=True)
    payload = b"pending-delete"
    path.write_bytes(payload)
    plan_id = uuid4()
    asset_id = "asset:interrupted"
    with database.unit_of_work() as session:
        session.add(
            LibraryDeletionPlanRecord(
                id=plan_id,
                state="running",
                summary={"assets": [str(path)]},
            )
        )
        session.flush()
        session.add(
            LibraryDeletionItemRecord(
                id=uuid4(),
                plan_id=plan_id,
                kind="asset",
                target_id=asset_id,
                category="original",
                path=str(path),
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
                state="pending",
            )
        )

    repository = LibraryRepository(database, (root,))

    assert repository.recover_deletions() == 1
    with database.unit_of_work() as session:
        plan = session.get(LibraryDeletionPlanRecord, plan_id)
        item = session.scalar(
            select(LibraryDeletionItemRecord).where(
                LibraryDeletionItemRecord.plan_id == plan_id
            )
        )
    assert plan is not None and plan.state == "partial"
    assert plan.error_code == "DELETE_INTERRUPTED"
    assert item is not None and item.state == "failed"
    assert path.read_bytes() == payload
    database.close()
