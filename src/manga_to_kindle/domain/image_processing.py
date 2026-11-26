"""Modelos imutáveis para importação local e derivados de imagem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from manga_to_kindle.domain.errors import DomainValidationError


class ImageProcessingError(RuntimeError):
    code = "IMAGE_PROCESSING_FAILED"


class ImageSourceRejected(ImageProcessingError):
    code = "IMAGE_SOURCE_REJECTED"


class ImageLimitExceeded(ImageProcessingError):
    code = "IMAGE_LIMIT_EXCEEDED"


class ImageContentRejected(ImageProcessingError):
    code = "IMAGE_CONTENT_REJECTED"


class ImageTargetConflict(ImageProcessingError):
    """Destino local ausente, demonstrativo ou já preenchido com outro lote."""

    code = "IMAGE_TARGET_CONFLICT"


class ImageImportCancelled(ImageProcessingError):
    code = "IMAGE_IMPORT_CANCELLED"

MAX_SOURCE_ENTRIES = 10_000
MAX_IMAGES_PER_SOURCE = 5_000
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_SOURCE_IMAGE_BYTES = 2 * 1024 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
SUPPORTED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


class ImageSourceKind(StrEnum):
    DIRECTORY = "directory"
    CBZ = "cbz"


class ReadingDirection(StrEnum):
    RIGHT_TO_LEFT = "rtl"
    LEFT_TO_RIGHT = "ltr"


@dataclass(frozen=True, slots=True)
class ImageSourceFile:
    relative_path: str
    locator: str
    declared_size: int
    is_directory: bool = False


@dataclass(frozen=True, slots=True)
class ImageSourceManifest:
    kind: ImageSourceKind
    files: tuple[ImageSourceFile, ...]
    ignored_entries: int


@dataclass(frozen=True, slots=True)
class ScannedImage:
    relative_path: str
    locator: str
    byte_size: int
    sha256: str
    media_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ImageInspection:
    image_format: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ImageImportPlan:
    source_path: Path
    source_kind: ImageSourceKind
    images: tuple[ScannedImage, ...]
    ignored_entries: int
    total_image_bytes: int
    fingerprint: str

    def __post_init__(self) -> None:
        if not self.images:
            raise DomainValidationError("A prévia precisa conter ao menos uma imagem.")
        if self.ignored_entries < 0 or self.total_image_bytes < 0:
            raise DomainValidationError("A prévia contém contagens inválidas.")
        paths = tuple(image.relative_path for image in self.images)
        if len(paths) != len(set(paths)):
            raise DomainValidationError("A prévia contém caminhos repetidos.")


@dataclass(frozen=True, slots=True)
class ImageImportTarget:
    manga_id: UUID
    chapter_id: UUID
    manga_title: str | None = None
    chapter_title: str | None = None
    chapter_number: str | None = None
    create_new: bool = False

    def __post_init__(self) -> None:
        if self.create_new:
            if self.manga_title is None or not self.manga_title.strip():
                raise DomainValidationError("Informe o título do mangá local.")
            if self.chapter_title is None and self.chapter_number is None:
                raise DomainValidationError("Informe o título ou número do capítulo local.")
            if self.chapter_title is not None and not self.chapter_title.strip():
                raise DomainValidationError("O título do capítulo não pode ser vazio.")
            if self.chapter_number is not None and not self.chapter_number.strip():
                raise DomainValidationError("O número do capítulo não pode ser vazio.")
        elif self.manga_title is not None or self.chapter_title is not None:
            raise DomainValidationError("Um destino existente não recebe novos títulos.")


@dataclass(frozen=True, slots=True)
class ImageProcessingProfile:
    name: str = "Kindle Básico 10ª geração"
    width: int = 600
    height: int = 800
    margin_left: int = 0
    margin_top: int = 0
    margin_right: int = 0
    margin_bottom: int = 0

    def __post_init__(self) -> None:
        if self.name != "Kindle Básico 10ª geração":
            raise DomainValidationError("O perfil de processamento não é compatível.")
        if (self.width, self.height) != (600, 800):
            raise DomainValidationError("O perfil inicial precisa medir 600×800 pixels.")
        margins = (self.margin_left, self.margin_top, self.margin_right, self.margin_bottom)
        if any(margin < 0 or margin > 40 for margin in margins):
            raise DomainValidationError("As margens precisam ficar entre 0 e 40 pixels.")
        if self.margin_left + self.margin_right >= self.width:
            raise DomainValidationError("As margens horizontais excedem o quadro.")
        if self.margin_top + self.margin_bottom >= self.height:
            raise DomainValidationError("As margens verticais excedem o quadro.")


@dataclass(frozen=True, slots=True)
class ImageTransformOptions:
    crop_margins: bool = False
    split_double_pages: bool = False
    reading_direction: ReadingDirection = ReadingDirection.RIGHT_TO_LEFT
    double_page_paths: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.split_double_pages and self.double_page_paths:
            raise DomainValidationError("Marque páginas duplas somente com a divisão ativa.")


@dataclass(frozen=True, slots=True)
class ImageImportChapterTarget:
    manga_id: UUID
    chapter_id: UUID
    manga_title: str
    chapter_title: str
    chapter_number: str | None
    has_imported_pages: bool = False


@dataclass(frozen=True, slots=True)
class ImageImportResult:
    job_id: UUID
    imported_pages: int
    processed_pages: int
    duplicate_content_count: int
    idempotent: bool = False


@dataclass(frozen=True, slots=True)
class StagedProcessedImage:
    output_order: int
    staged_path: Path
    final_path: Path
    sha256: str
    width: int = 600
    height: int = 800


@dataclass(frozen=True, slots=True)
class StagedImagePage:
    page_id: UUID
    relative_path: str
    position: int
    staged_original_path: Path
    final_original_path: Path
    original_sha256: str
    media_type: str
    width: int
    height: int
    duplicate_content: bool
    processed: tuple[StagedProcessedImage, ...]


@dataclass(frozen=True, slots=True)
class ImportedPage:
    id: UUID = field(default_factory=uuid4)
    relative_path: str = ""
    position: int = 0
    original_path: Path = Path()
    sha256: str = ""
    media_type: str = ""
    width: int = 0
    height: int = 0
    duplicate_content: bool = False


@dataclass(frozen=True, slots=True)
class ProcessedPage:
    page_id: UUID
    output_order: int
    path: Path
    sha256: str
    width: int = 600
    height: int = 800
