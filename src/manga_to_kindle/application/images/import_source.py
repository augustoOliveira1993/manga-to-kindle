"""Pré-valida fontes locais antes de iniciar qualquer gravação final."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from manga_to_kindle.application.images.errors import (
    ImageContentRejected,
    ImageImportCancelled,
    ImageLimitExceeded,
    ImageSourceRejected,
)
from manga_to_kindle.domain.image_processing import (
    MAX_IMAGE_BYTES,
    MAX_IMAGES_PER_SOURCE,
    MAX_SOURCE_IMAGE_BYTES,
    SUPPORTED_IMAGE_FORMATS,
    ImageImportPlan,
    ImageInspection,
    ImageProcessingProfile,
    ImageSourceFile,
    ImageSourceManifest,
    ImageTransformOptions,
    ScannedImage,
)


class CancellationSignal(Protocol):
    @property
    def cancelled(self) -> bool: ...


class ImageSourceReader(Protocol):
    def enumerate(self, source_path: Path) -> ImageSourceManifest: ...

    def read(self, source_path: Path, source_file: ImageSourceFile, limit: int) -> bytes: ...


class ImageDecoder(Protocol):
    def inspect(self, data: bytes, expected_format: str) -> ImageInspection: ...

    def transform(
        self,
        data: bytes,
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
        *,
        is_double_page: bool,
    ) -> tuple[bytes, ...]: ...

    def preview(
        self,
        data: bytes,
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
        *,
        is_double_page: bool,
    ) -> tuple[bytes, ...]: ...


type ProgressCallback = Callable[[int, int, str], None]


def natural_sort_key(value: str) -> tuple[tuple[int, int | str], ...]:
    """Ordena trechos numéricos sem depender da ordem do sistema de arquivos."""

    tokens = re.split(r"(\d+)", value.casefold())
    return tuple(
        (0, int(token)) if token.isdigit() else (1, token)
        for token in tokens
        if token
    )


def order_image_paths(paths: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(paths, key=lambda item: (natural_sort_key(item), item.casefold(), item)))


class ScanImageSource:
    def __init__(self, source_reader: ImageSourceReader, decoder: ImageDecoder) -> None:
        self._source_reader = source_reader
        self._decoder = decoder

    def execute(
        self,
        source_path: Path,
        *,
        cancellation: CancellationSignal | None = None,
        report_progress: ProgressCallback | None = None,
    ) -> ImageImportPlan:
        candidate_source = source_path.expanduser()
        manifest = self._source_reader.enumerate(candidate_source)
        resolved_source = candidate_source.resolve(strict=True)
        candidates: list[tuple[ImageSourceFile, str]] = []
        ignored = manifest.ignored_entries
        for entry in manifest.files:
            if entry.is_directory:
                ignored += 1
                continue
            extension = Path(entry.relative_path).suffix.lower()
            expected_format = SUPPORTED_IMAGE_FORMATS.get(extension)
            if expected_format is None:
                ignored += 1
                continue
            candidates.append((entry, expected_format))
        if len(candidates) > MAX_IMAGES_PER_SOURCE:
            raise ImageLimitExceeded("A origem contém mais de 5.000 imagens.")
        scanned: list[ScannedImage] = []
        total_bytes = 0
        report = report_progress or (lambda _done, _total, _stage: None)
        for index, (entry, expected_format) in enumerate(candidates, start=1):
            if cancellation is not None and cancellation.cancelled:
                raise ImageImportCancelled("A leitura da origem foi cancelada.")
            if entry.declared_size > MAX_IMAGE_BYTES:
                raise ImageLimitExceeded("Uma imagem excede o limite de 25 MiB.")
            total_bytes += entry.declared_size
            if total_bytes > MAX_SOURCE_IMAGE_BYTES:
                raise ImageLimitExceeded("As imagens excedem o limite total de 2 GiB.")
            data = self._source_reader.read(resolved_source, entry, MAX_IMAGE_BYTES)
            if len(data) > MAX_IMAGE_BYTES:
                raise ImageLimitExceeded("Uma imagem excede o limite de 25 MiB.")
            if len(data) != entry.declared_size:
                raise ImageSourceRejected("O tamanho da imagem mudou durante a leitura.")
            inspection = self._decoder.inspect(data, expected_format)
            media_format = (
                "jpeg" if inspection.image_format == "JPEG" else inspection.image_format.lower()
            )
            scanned.append(
                ScannedImage(
                    relative_path=entry.relative_path,
                    locator=entry.locator,
                    byte_size=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                    media_type=f"image/{media_format}",
                    width=inspection.width,
                    height=inspection.height,
                )
            )
            report(index, len(candidates), f"Imagem {index} de {len(candidates)} verificada")
        if not scanned:
            raise ImageSourceRejected("A origem não contém imagens JPEG, PNG ou WEBP válidas.")
        scanned.sort(
            key=lambda image: (
                natural_sort_key(image.relative_path),
                image.relative_path.casefold(),
                image.relative_path,
            )
        )
        fingerprint_hash = hashlib.sha256()
        for image in scanned:
            fingerprint_hash.update(image.relative_path.casefold().encode("utf-8"))
            fingerprint_hash.update(b"\0")
            fingerprint_hash.update(image.sha256.encode("ascii"))
            fingerprint_hash.update(b"\n")
        return ImageImportPlan(
            source_path=resolved_source,
            source_kind=manifest.kind,
            images=tuple(scanned),
            ignored_entries=ignored,
            total_image_bytes=sum(image.byte_size for image in scanned),
            fingerprint=fingerprint_hash.hexdigest(),
        )


class ImageReaderError(RuntimeError):
    """Falha segura da leitura de diretório ou arquivo CBZ."""


def ensure_supported_format(relative_path: str, image_format: str) -> None:
    expected = SUPPORTED_IMAGE_FORMATS.get(Path(relative_path).suffix.lower())
    if expected is None or image_format != expected:
        raise ImageContentRejected("A extensão e o conteúdo real da imagem não correspondem.")
