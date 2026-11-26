from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import ExportFormat, ExportGrouping, ExportRequest
from manga_to_kindle.domain.image_processing import ImageImportTarget, ReadingDirection
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.models import (
    ExportArtifactRecord,
    ExportRecord,
    PageRecord,
)
from tests.image_support import FIXTURES, make_image_stack, make_new_target


def _make_flow(
    tmp_path: Path,
) -> tuple[SQLiteDatabase, ImageImportTarget, Path, bytes, tuple[CreateExport, ExportRepository]]:
    database, image_root, _store, _image_repository, _reader, _decoder, importer = (
        make_image_stack(tmp_path)
    )
    target = make_new_target("Coleção exportável", "Capítulo 1")
    source_path = FIXTURES / "valid" / "pagina_1.png"
    source_bytes = source_path.read_bytes()
    plan = importer.preview_source(FIXTURES / "valid")
    importer.execute(plan, target, confirmed_authorization=True)
    repository = ExportRepository(database)
    workflow = CreateExport(
        repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
    )
    return database, target, image_root, source_bytes, (workflow, repository)


def _request(
    target: ImageImportTarget,
    output_directory: Path,
    format: ExportFormat,
) -> ExportRequest:
    return ExportRequest(
        chapter_ids=(target.chapter_id,),
        output_directory=output_directory.resolve(),
        profile=DeviceProfile("Leitor 600 × 800", preferences={"width": 600, "height": 800}),
        format=format,
        grouping=ExportGrouping.CHAPTER,
        direction=ReadingDirection.RIGHT_TO_LEFT,
        language="pt-BR" if format is ExportFormat.EPUB else None,
    )


def test_export_from_imported_processed_pages_is_published_and_recorded(
    tmp_path: Path,
) -> None:
    database, target, image_root, source_bytes, (workflow, repository) = _make_flow(tmp_path)
    output_directory = tmp_path / "saida"
    output_directory.mkdir()
    with database.unit_of_work() as session:
        page_paths = tuple(session.scalars(select(PageRecord.original_path)))
    original_paths_before = tuple(
        (Path(path), hashlib.sha256(Path(path).read_bytes()).hexdigest()) for path in page_paths
    )

    result = workflow.execute(
        _request(target, output_directory, ExportFormat.EPUB),
    )

    assert len(result.output_paths) == 1
    assert result.output_paths[0].exists()
    assert result.total_bytes == result.output_paths[0].stat().st_size
    assert ValidateEpub().execute(result.output_paths[0]).page_count == 3
    assert source_bytes == (FIXTURES / "valid" / "pagina_1.png").read_bytes()
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in original_paths_before
    )
    choices = repository.list_exportable_chapters()
    assert any(
        choice.chapter_id == target.chapter_id and choice.page_count == 3 for choice in choices
    )
    with database.unit_of_work() as session:
        export = session.get(ExportRecord, UUID(result.export_id))
        artifacts = tuple(session.scalars(select(ExportArtifactRecord)))
    assert export is not None and export.state == "completed"
    assert export.profile_snapshot["format"] == "epub"
    assert len(artifacts) == 1 and artifacts[0].path == str(result.output_paths[0])
    assert artifacts[0].chapter_ids == [str(target.chapter_id)]
    database.close()


def test_cbz_export_keeps_page_bytes_and_never_claims_a_reader_direction(
    tmp_path: Path,
) -> None:
    database, target, _image_root, _source_bytes, (workflow, _repository) = _make_flow(tmp_path)
    output_directory = tmp_path / "cbz"
    output_directory.mkdir()

    result = workflow.execute(_request(target, output_directory, ExportFormat.CBZ))

    assert result.output_paths[0].suffix == ".cbz"
    assert result.page_count == 3
    database.close()
