from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import ExportFormat, ExportGrouping, ExportRequest
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.kcc_adapter import KccCliWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.models import (
    ExportArtifactRecord,
    ExportRecord,
    PageRecord,
)
from tests.image_support import FIXTURES, make_image_stack, make_new_target

pytestmark = pytest.mark.skipif(
    not os.environ.get("M2K_KCC_EXE"),
    reason="Set M2K_KCC_EXE to run the actual KCC 13.0.4 Windows CLI integration.",
)


def test_actual_kcc_cli_creates_and_records_mobi_from_processed_local_pages(
    tmp_path: Path,
) -> None:
    executable = Path(os.environ["M2K_KCC_EXE"])
    database, _image_root, _store, _image_repository, _reader, _decoder, importer = (
        make_image_stack(tmp_path)
    )
    target = make_new_target("Validação KCC real", "Capítulo sintético")
    source = FIXTURES / "valid"
    import_plan = importer.preview_source(source)
    importer.execute(import_plan, target, confirmed_authorization=True)
    repository = ExportRepository(database)
    workflow = CreateExport(
        repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
        KccCliWriter,
    )
    output_directory = tmp_path / "mobi-output"
    output_directory.mkdir()
    request = ExportRequest(
        chapter_ids=(target.chapter_id,),
        output_directory=output_directory.resolve(),
        profile=DeviceProfile(
            "Kindle Básico 600 × 800",
            preferences={"width": 600, "height": 800},
        ),
        format=ExportFormat.MOBI,
        grouping=ExportGrouping.CHAPTER,
        direction=ReadingDirection.RIGHT_TO_LEFT,
        language="pt-BR",
    )
    with database.unit_of_work() as session:
        original_signatures = tuple(
            (Path(path), Path(path).read_bytes())
            for path in session.scalars(select(PageRecord.original_path))
        )

    result = workflow.execute(request, kcc_executable=executable)

    assert len(result.output_paths) == 1
    mobi_path = result.output_paths[0]
    assert mobi_path.suffix == ".mobi"
    assert mobi_path.read_bytes()[60:68] == b"BOOKMOBI"
    assert result.page_count == 3
    assert all(path.read_bytes() == content for path, content in original_signatures)
    with database.unit_of_work() as session:
        artifacts = tuple(session.scalars(select(ExportArtifactRecord)))
        export = session.get(ExportRecord, UUID(result.export_id))
    assert len(artifacts) == 1
    assert artifacts[0].format == "mobi"
    assert artifacts[0].path == str(mobi_path)
    assert export is not None and export.state == "completed"
    assert repository.list_transfer_artifacts() == ()
    assert repository.get_artifact(artifacts[0].id) is None
    database.close()
