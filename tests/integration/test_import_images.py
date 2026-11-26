from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from sqlalchemy import func, select

from manga_to_kindle.application.images.errors import (
    ImageSourceRejected,
    ImageTargetConflict,
)
from manga_to_kindle.domain.image_processing import ImageImportTarget
from manga_to_kindle.infrastructure.persistence.models import (
    ImageImportJobRecord,
    MangaRecord,
)
from tests.image_support import FIXTURES, make_image_stack, make_new_target


def test_folder_import_publishes_originals_and_kindled_derivatives_atomically(
    tmp_path: Path,
) -> None:
    database, image_root, _store, repository, _reader, _decoder, importer = make_image_stack(
        tmp_path
    )
    source = FIXTURES / "valid"
    original_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.iterdir()
        if path.is_file()
    }
    plan = importer.preview_source(source)
    target = make_new_target("Coleção local", "Volume de teste")
    progress: list[tuple[int, int, str]] = []

    result = importer.execute(
        plan,
        target,
        confirmed_authorization=True,
        report_progress=lambda done, total, stage: progress.append((done, total, stage)),
    )

    pages = repository.get_pages(target.chapter_id)
    assert result.imported_pages == 3
    assert result.processed_pages == 3
    assert [page.position for page in pages] == [0, 1, 2]
    assert [page.source_relative_path for page in pages] == [
        "pagina_1.png",
        "pagina_2.jpg",
        "pagina_10.webp",
    ]
    assert all(page.original_path.startswith(str(image_root)) for page in pages)
    assert all(page.import_job_id == result.job_id for page in pages)
    assert progress[-1][0:2] == (3, 3)
    for page in pages:
        original_path = Path(page.original_path)
        assert hashlib.sha256(original_path.read_bytes()).hexdigest() == page.source_sha256
        for processed in repository.get_processed_pages(page.id):
            with Image.open(processed.path) as image:
                assert image.size == (600, 800)
                assert image.mode == "L"
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.iterdir()
        if path.is_file()
    } == original_hashes
    assert repository.get_job(result.job_id).state == "succeeded"
    database.close()


def test_cbz_import_keeps_read_order_and_never_extracts_archive_names(tmp_path: Path) -> None:
    database, image_root, _store, repository, _reader, _decoder, importer = make_image_stack(
        tmp_path
    )
    plan = importer.preview_source(FIXTURES / "valid.cbz")
    target = make_new_target("CBZ local", "Capítulo CBZ")

    result = importer.execute(plan, target, confirmed_authorization=True)

    pages = repository.get_pages(target.chapter_id)
    assert result.imported_pages == 3
    assert [page.source_relative_path for page in pages] == [
        "capitulo/pagina_1.png",
        "capitulo/pagina_2.jpg",
        "capitulo/pagina_10.webp",
    ]
    assert all(Path(page.original_path).is_relative_to(image_root) for page in pages)
    assert not (tmp_path / "fora.png").exists()
    database.close()


def test_manual_order_is_the_persisted_reading_order(tmp_path: Path) -> None:
    database, _root, _store, repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")
    target = make_new_target()
    requested_order = tuple(image.relative_path for image in reversed(plan.images))

    importer.execute(
        plan,
        target,
        confirmed_authorization=True,
        ordered_paths=requested_order,
    )

    pages = repository.get_pages(target.chapter_id)
    assert [page.source_relative_path for page in pages] == list(requested_order)
    database.close()


def test_duplicate_bytes_at_distinct_positions_are_preserved_and_reported(tmp_path: Path) -> None:
    source = tmp_path / "duplicate-source"
    source.mkdir()
    contents = (FIXTURES / "valid" / "pagina_1.png").read_bytes()
    (source / "pagina1.png").write_bytes(contents)
    (source / "pagina2.png").write_bytes(contents)
    database, _root, _store, repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(source)
    target = make_new_target()

    result = importer.execute(plan, target, confirmed_authorization=True)

    pages = repository.get_pages(target.chapter_id)
    assert result.imported_pages == 2
    assert result.duplicate_content_count == 1
    assert len({page.id for page in pages}) == 2
    assert [page.duplicate_content for page in pages] == [False, True]
    database.close()


def test_identical_reimport_is_idempotent_and_does_not_duplicate_pages(tmp_path: Path) -> None:
    database, _root, _store, repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")
    created_target = make_new_target()
    importer.execute(plan, created_target, confirmed_authorization=True)
    existing_target = ImageImportTarget(
        manga_id=created_target.manga_id,
        chapter_id=created_target.chapter_id,
    )

    repeated = importer.execute(plan, existing_target, confirmed_authorization=True)

    assert repeated.idempotent is True
    assert repeated.imported_pages == 0
    assert len(repository.get_pages(existing_target.chapter_id)) == 3
    database.close()


def test_reimport_with_changed_content_leaves_existing_pages_untouched(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "pagina1.png"
    source_file.write_bytes((FIXTURES / "valid" / "pagina_1.png").read_bytes())
    original_bytes = source_file.read_bytes()
    database, _root, _store, repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    initial_plan = importer.preview_source(source)
    created = make_new_target()
    importer.execute(initial_plan, created, confirmed_authorization=True)
    old_page = repository.get_pages(created.chapter_id)[0]
    with Image.open(source_file) as changed_source:
        changed = changed_source.copy()
    ImageDraw.Draw(changed).rectangle((0, 0, 15, 15), fill="#000000")
    changed.save(source_file, format="PNG")
    changed_plan = importer.preview_source(source)
    target = ImageImportTarget(manga_id=created.manga_id, chapter_id=created.chapter_id)

    with pytest.raises(ImageTargetConflict):
        importer.execute(changed_plan, target, confirmed_authorization=True)

    pages = repository.get_pages(created.chapter_id)
    assert len(pages) == 1 and pages[0].id == old_page.id
    assert Path(pages[0].original_path).read_bytes() == original_bytes
    assert pages[0].source_sha256 != hashlib.sha256(source_file.read_bytes()).hexdigest()
    with database.unit_of_work() as session:
        jobs = tuple(session.scalars(select(ImageImportJobRecord)))
    assert jobs[-1].state == "failed"
    database.close()


def test_changed_source_after_preview_aborts_before_publishing_any_page(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "pagina1.png"
    source_file.write_bytes((FIXTURES / "valid" / "pagina_1.png").read_bytes())
    database, image_root, _store, repository, _reader, _decoder, importer = make_image_stack(
        tmp_path
    )
    plan = importer.preview_source(source)
    source_file.write_bytes((FIXTURES / "valid" / "pagina_2.jpg").read_bytes())
    target = make_new_target()

    with pytest.raises(ImageSourceRejected):
        importer.execute(plan, target, confirmed_authorization=True)

    with database.unit_of_work() as session:
        manga_count = session.scalar(select(func.count()).select_from(MangaRecord))
        job = session.scalar(select(ImageImportJobRecord))
    assert manga_count == 0
    assert job is not None and job.state == "failed"
    assert not repository.get_pages(target.chapter_id)
    assert not list((image_root / "imports").glob("*"))
    assert not list((image_root / ".staging").glob("*"))
    database.close()


def test_authorization_confirmation_is_required_before_job_creation(tmp_path: Path) -> None:
    database, _root, _store, _repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")

    with pytest.raises(ImageSourceRejected, match="autorização"):
        importer.execute(plan, make_new_target(), confirmed_authorization=False)

    with database.unit_of_work() as session:
        assert session.scalar(select(func.count()).select_from(ImageImportJobRecord)) == 0
    database.close()
