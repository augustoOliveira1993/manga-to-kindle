from __future__ import annotations

from pathlib import Path

from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import ExportFormat, ExportGrouping, ExportRequest
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.library import LibraryQuery
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from tests.image_support import FIXTURES, make_image_stack, make_new_target


def test_import_and_export_history_keep_identity_after_manga_removal(tmp_path: Path) -> None:
    database, image_root, _store, _repo, _reader, _decoder, importer = make_image_stack(tmp_path)
    target = make_new_target("Histórico preservado", "Capítulo 7")
    plan = importer.preview_source(FIXTURES / "valid")
    importer.execute(plan, target, confirmed_authorization=True)
    export_repository = ExportRepository(database)
    workflow = CreateExport(
        export_repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
    )
    output_directory = tmp_path / "exports"
    output_directory.mkdir()
    workflow.execute(
        ExportRequest(
            chapter_ids=(target.chapter_id,),
            output_directory=output_directory,
            profile=DeviceProfile("Leitor de teste", preferences={"width": 600, "height": 800}),
            format=ExportFormat.EPUB,
            grouping=ExportGrouping.CHAPTER,
            direction=ReadingDirection.RIGHT_TO_LEFT,
            language="pt-BR",
        )
    )
    repository = LibraryRepository(database, (image_root,))
    before = repository.history()
    completed_exports = repository.search(LibraryQuery(export_state="completed"))
    assert any(item.identity == "Histórico preservado — Capítulo 7" for item in before)
    assert any(
        item.identity == "Histórico preservado — Capítulo 7 · EPUB" for item in before
    )
    assert any(item.chapter_id == target.chapter_id for item in completed_exports.entries)

    preview = repository.preview_delete(target.manga_id)
    repository.delete_scope(preview, asset_ids=(), confirmed=True)
    after = repository.history()

    assert any(item.identity == "Histórico preservado — Capítulo 7" for item in after)
    assert any(
        item.identity == "Histórico preservado — Capítulo 7 · EPUB" for item in after
    )
    database.close()
