"""Contratos imutáveis de planejamento de exportação local."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.image_processing import ReadingDirection


class ExportFormat(StrEnum):
    EPUB = "epub"
    CBZ = "cbz"
    MOBI = "mobi"


class ExportGrouping(StrEnum):
    CHAPTER = "chapter"
    VOLUME = "volume"


@dataclass(frozen=True, slots=True)
class ExportableChapter:
    manga_id: UUID
    chapter_id: UUID
    manga_title: str
    chapter_title: str
    page_count: int
    language: str | None = None
    volume: str | None = None


@dataclass(frozen=True, slots=True)
class ExportedArtifact:
    package_id: UUID
    format: ExportFormat
    path: Path
    sha256: str
    size_bytes: int
    chapter_ids: tuple[UUID, ...]
    position: int

    def __post_init__(self) -> None:
        if not self.path.is_absolute() or self.size_bytes <= 0 or self.position < 0:
            raise DomainValidationError("O artefato publicado tem dados inválidos.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise DomainValidationError("O checksum do artefato publicado é inválido.")
        if not self.chapter_ids:
            raise DomainValidationError("O artefato precisa referenciar capítulos.")


@dataclass(frozen=True, slots=True)
class ExportAsset:
    path: Path
    sha256: str
    media_type: str
    width: int
    height: int
    output_order: int = 0
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise DomainValidationError("O arquivo processado precisa ter caminho absoluto.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise DomainValidationError("O checksum da página processada é inválido.")
        if self.media_type != "image/png":
            raise DomainValidationError("A exportação aceita somente páginas processadas em PNG.")
        if self.width <= 0 or self.height <= 0 or self.output_order < 0:
            raise DomainValidationError("As dimensões e a ordem da página precisam ser válidas.")


@dataclass(frozen=True, slots=True)
class ExportPage:
    id: UUID
    position: int
    processed: tuple[ExportAsset, ...]

    def __post_init__(self) -> None:
        if self.position < 0 or not self.processed:
            raise DomainValidationError("Cada página precisa de posição e derivado processado.")
        orders = tuple(asset.output_order for asset in self.processed)
        if orders != tuple(range(len(orders))):
            raise DomainValidationError("Os derivados da página precisam ter ordem contínua.")


@dataclass(frozen=True, slots=True)
class ExportSourceChapter:
    chapter: Chapter
    manga_title: str
    pages: tuple[ExportPage, ...]
    volume: str | None = None
    author: str | None = None
    language: str | None = None
    cover: ExportAsset | None = None

    def __post_init__(self) -> None:
        if not self.manga_title.strip():
            raise DomainValidationError("O mangá precisa ter título antes da exportação.")
        if not self.pages:
            raise DomainValidationError("O capítulo não contém páginas processadas.")
        positions = tuple(page.position for page in self.pages)
        if positions != tuple(range(len(positions))):
            raise DomainValidationError("As páginas precisam estar completas e em ordem.")
        if self.volume is not None and not self.volume.strip():
            raise DomainValidationError("O volume conhecido não pode ser vazio.")
        if self.author is not None and not self.author.strip():
            raise DomainValidationError("O autor informado não pode ser vazio.")
        if self.language is not None and not _LANGUAGE_PATTERN.fullmatch(self.language):
            raise DomainValidationError("O idioma informado não é válido.")


@dataclass(frozen=True, slots=True)
class ExportRequest:
    chapter_ids: tuple[UUID, ...]
    output_directory: Path
    profile: DeviceProfile
    format: ExportFormat
    grouping: ExportGrouping = ExportGrouping.CHAPTER
    direction: ReadingDirection = ReadingDirection.RIGHT_TO_LEFT
    language: str | None = None
    max_size_bytes: int | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.chapter_ids or len(self.chapter_ids) != len(set(self.chapter_ids)):
            raise DomainValidationError("Selecione capítulos únicos para exportar.")
        if not self.output_directory.is_absolute():
            raise DomainValidationError("A pasta de saída precisa ser um caminho absoluto.")
        if self.max_size_bytes is not None and self.max_size_bytes <= 0:
            raise DomainValidationError("O limite de tamanho precisa ser maior que zero.")
        if self.language is not None and not _LANGUAGE_PATTERN.fullmatch(self.language):
            raise DomainValidationError("Selecione um idioma válido.")


@dataclass(frozen=True, slots=True)
class PlannedImage:
    chapter_id: UUID
    page_id: UUID
    page_position: int
    asset: ExportAsset


@dataclass(frozen=True, slots=True)
class ExportPackagePlan:
    id: UUID
    title: str
    filename: str
    chapter_ids: tuple[UUID, ...]
    chapter_titles: tuple[tuple[UUID, str], ...]
    pages: tuple[PlannedImage, ...]
    volume: str | None
    cover: ExportAsset | None
    identifier: str


@dataclass(frozen=True, slots=True)
class GeneratedPackage:
    package_id: UUID
    path: Path
    sha256: str
    size_bytes: int
    page_count: int

    def __post_init__(self) -> None:
        if not self.path.is_absolute() or self.size_bytes <= 0 or self.page_count <= 0:
            raise DomainValidationError("O pacote gerado tem dados inválidos.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise DomainValidationError("O checksum do pacote gerado é inválido.")


@dataclass(frozen=True, slots=True)
class ExportPlan:
    id: UUID
    format: ExportFormat
    grouping: ExportGrouping
    direction: ReadingDirection
    profile: DeviceProfile
    output_directory: Path
    language: str | None
    author: str | None
    max_size_bytes: int | None
    packages: tuple[ExportPackagePlan, ...]


_LANGUAGE_PATTERN = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = re.compile(r"(?i)^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$")


def sanitize_filename_component(value: str, *, fallback: str = "export") -> str:
    """Remove componentes de caminho e nomes reservados sem alterar metadados do livro."""

    cleaned = _INVALID_FILENAME.sub("_", value).rstrip(" .")
    cleaned = cleaned[:120].rstrip(" .")
    cleaned = cleaned.lstrip(".")
    if not cleaned or cleaned in {".", ".."} or _WINDOWS_RESERVED.fullmatch(cleaned):
        return fallback
    return cleaned
