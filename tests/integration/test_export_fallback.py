from __future__ import annotations

import socket
from pathlib import Path

from manga_to_kindle.application.bootstrap import bootstrap_application
from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import ExportFormat, ExportRequest
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.image_import_repository import (
    ImageImportRepository,
)
from tests.image_support import FIXTURES, make_new_target


def test_native_epub_is_available_without_kcc_or_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def reject_network(*_args, **_kwargs):
        raise AssertionError("A exportação nativa tentou consultar KCC ou abrir a rede.")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)

    runtime = bootstrap_application(AppPaths.from_root(tmp_path / "profile"))
    try:
        database = runtime.database
        image_root = runtime.paths.data / "images"
        image_repository = ImageImportRepository(database, image_root)
        importer = ImportImages(
            LocalImageSourceReader(),
            PillowImageDecoder(),
            ImageStore(image_root),
            image_repository,
        )
        target = make_new_target("Fallback nativo", "Capítulo 1")
        import_plan = importer.preview_source(FIXTURES / "valid")
        importer.execute(import_plan, target, confirmed_authorization=True)
        repository = ExportRepository(database)
        workflow = CreateExport(
            repository,
            ExportOutputStore,
            NativeEpubWriter(),
            NativeCbzWriter(),
            ValidateEpub(),
            ValidateCbz(),
        )
        output = tmp_path / "saida"
        output.mkdir()
        request = ExportRequest(
            chapter_ids=(target.chapter_id,),
            output_directory=output.resolve(),
            profile=DeviceProfile("Páginas F006", preferences={"width": 600, "height": 800}),
            format=ExportFormat.EPUB,
            direction=ReadingDirection.RIGHT_TO_LEFT,
            language="pt-BR",
        )
        result = workflow.execute(request)

        assert len(result.output_paths) == 1
        assert result.output_paths[0].suffix == ".epub"
        assert ValidateEpub().execute(result.output_paths[0]).page_count == 3
    finally:
        runtime.shutdown()
