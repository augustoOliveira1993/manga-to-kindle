"""Contratos imutáveis para consulta e histórico da biblioteca local."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.errors import DomainValidationError


class AvailabilityState(StrEnum):
    DOWNLOADED = "downloaded"
    PARTIAL = "partial"
    NOT_DOWNLOADED = "not_downloaded"
    IMPORTED = "imported"
    MISSING = "missing"
    ALTERED = "altered"


class LibrarySort(StrEnum):
    TITLE = "title"
    ACTIVITY = "activity"
    STATE = "state"
    CHAPTER = "chapter"


class ActivityKind(StrEnum):
    DOWNLOAD = "download"
    IMAGE_IMPORT = "image_import"
    EXPORT = "export"


class LibraryAssetCategory(StrEnum):
    ORIGINAL = "original"
    PROCESSED = "processed"
    DOWNLOAD = "download"
    EXPORT = "export"


class LibraryAssetState(StrEnum):
    AVAILABLE = "available"
    UNLINKED = "unlinked"
    MISSING = "missing"
    CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class LibraryQuery:
    search_text: str = ""
    favorite_only: bool = False
    availability: AvailabilityState | None = None
    download_state: str | None = None
    export_state: str | None = None
    sort: LibrarySort = LibrarySort.TITLE
    offset: int = 0
    limit: int = 100

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise DomainValidationError("O início da página da biblioteca não pode ser negativo.")
        if not 1 <= self.limit <= 500:
            raise DomainValidationError("A página da biblioteca deve conter de 1 a 500 itens.")
        if self.availability is not None and not isinstance(self.availability, AvailabilityState):
            raise DomainValidationError("O filtro de disponibilidade não é reconhecido.")
        if self.download_state not in {
            None,
            "queued",
            "running",
            "paused",
            "interrupted",
            "succeeded",
            "failed",
            "cancelled",
        }:
            raise DomainValidationError("O filtro de download não é reconhecido.")
        if self.export_state not in {
            None,
            "requested",
            "running",
            "completed",
            "failed",
            "cancelled",
            "missing",
            "altered",
        }:
            raise DomainValidationError("O filtro de exportação não é reconhecido.")
        if not isinstance(self.sort, LibrarySort):
            raise DomainValidationError("A ordenação da biblioteca não é reconhecida.")

    @property
    def normalized_search(self) -> str:
        return normalize_search_text(self.search_text)


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    manga_id: UUID
    manga_title: str
    author: str | None
    manga_favorite: bool
    chapter_id: UUID | None
    chapter_title: str | None
    chapter_number: str | None
    volume: str | None
    chapter_position: int | None
    chapter_favorite: bool
    availability: AvailabilityState
    page_count: int
    page_total: int | None
    download_state: str | None
    export_state: str | None
    updated_at: datetime
    simulated: bool

    @property
    def display_title(self) -> str:
        if self.chapter_id is None:
            return self.manga_title
        chapter_name = self.chapter_title or f"Capítulo {self.chapter_number or ''}".strip()
        return f"{self.manga_title} — {chapter_name}"


@dataclass(frozen=True, slots=True)
class LibraryPage:
    entries: tuple[LibraryEntry, ...]
    total: int


@dataclass(frozen=True, slots=True)
class LibraryActivity:
    id: UUID
    kind: ActivityKind
    identity: str
    state: str
    started_at: datetime
    ended_at: datetime
    reason_code: str | None = None
    location_name: str | None = None


@dataclass(frozen=True, slots=True)
class LibraryPreferences:
    favorite_only: bool = False
    availability: AvailabilityState | None = None
    download_state: str | None = None
    export_state: str | None = None
    sort: LibrarySort = LibrarySort.TITLE


@dataclass(frozen=True, slots=True)
class LibraryAsset:
    id: str
    category: LibraryAssetCategory
    path: Path
    sha256: str | None
    size_bytes: int
    media_type: str | None
    managed: bool
    state: LibraryAssetState
    shared: bool = False


@dataclass(frozen=True, slots=True)
class LibraryDeletionPreview:
    manga_id: UUID
    manga_title: str
    chapter_ids: tuple[UUID, ...]
    record_ids: tuple[tuple[str, str], ...]
    record_counts: tuple[tuple[str, int], ...]
    assets: tuple[LibraryAsset, ...]


@dataclass(frozen=True, slots=True)
class LibraryDeletionResult:
    plan_id: UUID
    state: str
    removed_record_count: int
    removed_file_count: int
    preserved_file_count: int
    error_code: str | None = None


def normalize_search_text(value: str) -> str:
    """Normaliza caixa, espaços e diacríticos sem perder caracteres Unicode-base."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.split())
