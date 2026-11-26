"""Staging de imagens raster sem transformar os bytes originais."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from PySide6.QtGui import QImageReader

from manga_to_kindle.application.downloads.errors import (
    DownloadCancelled,
    DownloadIdentityConflict,
    DownloadImageInvalid,
    DownloadStorageError,
)
from manga_to_kindle.infrastructure.downloads.transport import CancellationSignal

MAX_COMPRESSED_BYTES = 25 * 1024 * 1024
MAX_DECODED_PIXELS = 50_000_000
_MIME_FORMATS = {
    "image/jpeg": ("jpeg", ".jpg"),
    "image/png": ("png", ".png"),
    "image/webp": ("webp", ".webp"),
}


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    content_type: str
    format: str
    width: int
    height: int
    byte_size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class StagedArtifact:
    temporary_path: Path
    final_path: Path
    image: ValidatedImage


class PageStore:
    """Gerencia somente caminhos internos e cria o nome final sem sobrescrita."""

    def __init__(
        self,
        managed_root: Path,
        *,
        max_compressed_bytes: int = MAX_COMPRESSED_BYTES,
        max_decoded_pixels: int = MAX_DECODED_PIXELS,
    ) -> None:
        if not 0 < max_compressed_bytes <= MAX_COMPRESSED_BYTES:
            raise ValueError("O limite comprimido deve respeitar o teto da feature.")
        if not 0 < max_decoded_pixels <= MAX_DECODED_PIXELS:
            raise ValueError("O limite de pixels deve respeitar o teto da feature.")
        self.root = managed_root.expanduser().resolve()
        self.max_compressed_bytes = max_compressed_bytes
        self.max_decoded_pixels = max_decoded_pixels

    def stage_chunks(
        self,
        *,
        job_id: UUID,
        page_id: UUID,
        chapter_id: UUID,
        chunks: Iterable[bytes],
        content_type: str | None,
        cancellation: CancellationSignal,
    ) -> StagedArtifact:
        """Grava em fluxo com limite rígido, valida e devolve os dois caminhos internos."""
        if content_type is None:
            raise DownloadImageInvalid("O tipo da imagem não foi declarado.")
        normalized_type = content_type.split(";", maxsplit=1)[0].strip().lower()
        if normalized_type not in _MIME_FORMATS:
            raise DownloadImageInvalid("O tipo da imagem não é permitido.")

        temporary_path = self._temporary_path(job_id, page_id)
        final_parent = self.root / "pages" / str(chapter_id)
        created = False
        try:
            temporary_path.parent.mkdir(parents=True, exist_ok=True)
            final_parent.mkdir(parents=True, exist_ok=True)
            self._assert_managed(temporary_path.parent)
            self._assert_managed(final_parent)
            size = 0
            with temporary_path.open("xb") as stream:
                created = True
                for chunk in chunks:
                    if cancellation.cancelled:
                        raise DownloadCancelled("O download foi cancelado.")
                    if not isinstance(chunk, bytes):
                        raise DownloadImageInvalid("O transporte forneceu dados inválidos.")
                    size += len(chunk)
                    if size > self.max_compressed_bytes:
                        raise DownloadImageInvalid("A imagem excede o limite de tamanho.")
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            image = self.validate_file(temporary_path, normalized_type)
            extension = _MIME_FORMATS[normalized_type][1]
            final_path = final_parent / f"{page_id}{extension}"
            self._assert_managed(final_path.parent)
            return StagedArtifact(temporary_path, final_path, image)
        except (DownloadCancelled, DownloadImageInvalid):
            if created:
                self._remove_owned_partial(temporary_path, job_id, page_id)
            raise
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            if created:
                self._remove_owned_partial(temporary_path, job_id, page_id)
            raise DownloadStorageError("Não foi possível gravar a página localmente.") from exc

    def validate_file(self, path: Path, content_type: str) -> ValidatedImage:
        """Confere Content-Type, assinatura, dimensões e decodificação completa."""
        self._assert_managed(path)
        normalized_type = content_type.split(";", maxsplit=1)[0].strip().lower()
        format_info = _MIME_FORMATS.get(normalized_type)
        if format_info is None:
            raise DownloadImageInvalid("O tipo da imagem não é permitido.")
        try:
            byte_size = path.stat().st_size
            if byte_size <= 0 or byte_size > self.max_compressed_bytes:
                raise DownloadImageInvalid("O tamanho da imagem não é permitido.")
            with path.open("rb") as stream:
                signature = stream.read(16)
            image_format = _signature_format(signature)
            if image_format != format_info[0]:
                raise DownloadImageInvalid("O tipo declarado não corresponde à imagem.")

            reader = QImageReader(str(path))
            reader.setDecideFormatFromContent(True)
            image_size = reader.size()
            width, height = image_size.width(), image_size.height()
            if width <= 0 or height <= 0 or width * height > self.max_decoded_pixels:
                raise DownloadImageInvalid("As dimensões da imagem excedem o limite.")
            decoded = reader.read()
            if decoded.isNull() or decoded.width() != width or decoded.height() != height:
                raise DownloadImageInvalid("A imagem não pôde ser decodificada por completo.")
            digest = _sha256(path)
            return ValidatedImage(
                content_type=normalized_type,
                format=image_format,
                width=width,
                height=height,
                byte_size=byte_size,
                sha256=digest,
            )
        except DownloadImageInvalid:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise DownloadImageInvalid("A imagem não pôde ser validada.") from exc

    def promote(self, artifact: StagedArtifact, *, job_id: UUID, page_id: UUID) -> Path:
        """Publica por hard link atômico; uma página existente nunca é substituída."""
        self._assert_managed(artifact.temporary_path)
        self._assert_managed(artifact.final_path)
        try:
            if artifact.final_path.exists():
                existing = self.validate_file(artifact.final_path, artifact.image.content_type)
                if existing.sha256 != artifact.image.sha256:
                    self._remove_owned_partial(artifact.temporary_path, job_id, page_id)
                    raise DownloadIdentityConflict(
                        "A identidade da página já tem outro conteúdo."
                    ) from None
                self._remove_owned_partial(artifact.temporary_path, job_id, page_id)
                return artifact.final_path
            os.link(artifact.temporary_path, artifact.final_path)
            self._remove_owned_partial(artifact.temporary_path, job_id, page_id)
            return artifact.final_path
        except DownloadIdentityConflict:
            raise
        except FileExistsError:
            existing = self.validate_file(artifact.final_path, artifact.image.content_type)
            if existing.sha256 != artifact.image.sha256:
                self._remove_owned_partial(artifact.temporary_path, job_id, page_id)
                raise DownloadIdentityConflict(
                    "A identidade da página já tem outro conteúdo."
                ) from None
            self._remove_owned_partial(artifact.temporary_path, job_id, page_id)
            return artifact.final_path
        except OSError as exc:
            raise DownloadStorageError("Não foi possível finalizar a página atomicamente.") from exc

    def remove_partial(self, path: Path, *, job_id: UUID, page_id: UUID) -> bool:
        """Remove apenas o .part canônico do trabalho informado."""
        if path.resolve() != self._temporary_path(job_id, page_id).resolve():
            return False
        return self._remove_owned_partial(path, job_id, page_id)

    def temporary_path_for(self, job_id: UUID, page_id: UUID) -> Path:
        return self._temporary_path(job_id, page_id)

    def discard(self, artifact: StagedArtifact, *, job_id: UUID, page_id: UUID) -> bool:
        """Descarta um artefato staging ainda não promovido."""
        return self.remove_partial(artifact.temporary_path, job_id=job_id, page_id=page_id)

    def _temporary_path(self, job_id: UUID, page_id: UUID) -> Path:
        return self.root / "staging" / str(job_id) / f"{page_id}.part"

    def _remove_owned_partial(self, path: Path, job_id: UUID, page_id: UUID) -> bool:
        if path.resolve() != self._temporary_path(job_id, page_id).resolve():
            return False
        self._assert_managed(path)
        try:
            path.unlink(missing_ok=True)
            return True
        except OSError as exc:
            raise DownloadStorageError("Não foi possível limpar o temporário do trabalho.") from exc

    def _assert_managed(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise DownloadStorageError("O caminho saiu da área local gerenciada.") from None


def _signature_format(signature: bytes) -> str | None:
    if signature.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if signature[:4] == b"RIFF" and signature[8:12] == b"WEBP":
        return "webp"
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
