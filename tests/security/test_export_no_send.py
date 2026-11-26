from __future__ import annotations

import hashlib
import socket
from pathlib import Path
from uuid import UUID

from tests.export_support import fixture_sources, make_request

from manga_to_kindle.application.exports.create_export import CreateExport
from manga_to_kindle.application.exports.ports import ExportRepositoryPort
from manga_to_kindle.domain.exports import (
    ExportableChapter,
    ExportedArtifact,
    ExportFormat,
    ExportPlan,
    ExportSourceChapter,
)
from manga_to_kindle.infrastructure.exports.cbz_validator import ValidateCbz
from manga_to_kindle.infrastructure.exports.cbz_writer import NativeCbzWriter
from manga_to_kindle.infrastructure.exports.epub_validator import ValidateEpub
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter
from manga_to_kindle.infrastructure.exports.output_store import ExportOutputStore


class InMemoryExportRepository(ExportRepositoryPort):
    def __init__(self, sources: tuple[ExportSourceChapter, ...]) -> None:
        self.sources = sources
        self.state = ""
        self.artifacts: tuple[ExportedArtifact, ...] = ()

    def list_exportable_chapters(self) -> tuple[ExportableChapter, ...]:
        return ()

    def load_sources(self, chapter_ids: tuple[UUID, ...]) -> tuple[ExportSourceChapter, ...]:
        return tuple(source for source in self.sources if source.chapter.id in chapter_ids)

    def create(self, _plan: ExportPlan) -> None:
        self.state = "requested"

    def set_state(
        self,
        _export_id: UUID,
        state: str,
        *,
        error_code: str | None = None,
    ) -> None:
        self.state = state

    def complete(
        self,
        _export_id: UUID,
        artifacts: tuple[ExportedArtifact, ...],
    ) -> None:
        self.state = "completed"
        self.artifacts = artifacts


def test_epub_export_never_opens_network_or_changes_processed_inputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sources = fixture_sources()
    original_hashes = {
        asset.path: hashlib.sha256(asset.path.read_bytes()).hexdigest()
        for source in sources
        for page in source.pages
        for asset in page.processed
    }
    repository = InMemoryExportRepository(sources)
    workflow = CreateExport(
        repository,
        ExportOutputStore,
        NativeEpubWriter(),
        NativeCbzWriter(),
        ValidateEpub(),
        ValidateCbz(),
    )
    output_directory = tmp_path / "saidas"
    output_directory.mkdir()
    request = make_request(
        sources,
        chapter_indexes=(0, 1),
        format=ExportFormat.EPUB,
        output_directory=output_directory,
    )

    def reject_network(*_args, **_kwargs):
        raise AssertionError("A exportação local tentou abrir uma conexão de rede.")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)

    result = workflow.execute(request)

    assert repository.state == "completed"
    assert len(result.output_paths) == 2
    assert all(path.exists() and path.parent == output_directory for path in result.output_paths)
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for path, digest in original_hashes.items()
    )
