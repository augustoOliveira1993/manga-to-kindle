"""Valida um EPUB exportado e abre a pasta e o serviço oficial após ação explícita."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Protocol
from uuid import UUID

from manga_to_kindle.domain.transfers import ExportTransferArtifact, ManualFlowResult

SEND_TO_KINDLE_URL = "https://www.amazon.com/sendtokindle"


class ArtifactUnavailable(RuntimeError):
    code = "TRANSFER_ARTIFACT_UNAVAILABLE"


class TransferArtifactRepository(Protocol):
    def get_artifact(self, artifact_id: UUID) -> ExportTransferArtifact | None: ...


class SystemOpener(Protocol):
    def open_directory(self, path: Path) -> bool: ...

    def open_url(self, url: str) -> bool: ...


class OpenManualSend:
    def __init__(
        self,
        repository: TransferArtifactRepository,
        system_opener: SystemOpener,
    ) -> None:
        self._repository = repository
        self._system_opener = system_opener

    def execute(self, artifact_id: UUID) -> ManualFlowResult:
        artifact = self._repository.get_artifact(artifact_id)
        if artifact is None:
            raise ArtifactUnavailable("A exportação selecionada não está mais disponível.")
        if artifact.format != "epub" or artifact.path.suffix.casefold() != ".epub":
            raise ArtifactUnavailable(
                "O Send to Kindle manual oferece somente EPUBs exportados e validados."
            )
        verify_export_artifact(artifact)
        directory_opened = self._system_opener.open_directory(artifact.path.parent)
        page_opened = self._system_opener.open_url(SEND_TO_KINDLE_URL)
        return ManualFlowResult(artifact, directory_opened, page_opened)


def verify_export_artifact(artifact: ExportTransferArtifact) -> None:
    path = artifact.path
    try:
        if path.is_symlink():
            raise ArtifactUnavailable("O arquivo exportado não pode ser um link simbólico.")
        resolved = path.resolve(strict=True)
        if resolved != path:
            raise ArtifactUnavailable("O caminho do arquivo exportado foi alterado.")
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != artifact.size_bytes:
            raise ArtifactUnavailable("O arquivo exportado está ausente ou foi alterado.")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != artifact.sha256:
            raise ArtifactUnavailable("O checksum do arquivo exportado não corresponde.")
    except ArtifactUnavailable:
        raise
    except OSError:
        raise ArtifactUnavailable("Não foi possível verificar o arquivo exportado.") from None
