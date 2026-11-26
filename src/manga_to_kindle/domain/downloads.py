"""Identidades e estados persistentes de páginas de download."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.errors import DomainValidationError


class DownloadPageState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    STAGING = "staging"
    WAITING_RETRY = "waiting_retry"
    INTERRUPTED = "interrupted"
    COMPLETE = "complete"
    FAILED = "failed"


class DownloadChapterState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DownloadChapterProgress:
    chapter_id: UUID
    position: int
    state: DownloadChapterState
    page_total: int | None
    page_completed: int

    def __post_init__(self) -> None:
        if self.position < 0 or self.page_completed < 0:
            raise DomainValidationError("O progresso do capítulo precisa ser válido.")
        if self.page_total is not None and (
            self.page_total < 0 or self.page_completed > self.page_total
        ):
            raise DomainValidationError("O progresso do capítulo excede o total conhecido.")


@dataclass(frozen=True, slots=True)
class DownloadPage:
    id: UUID
    job_id: UUID
    chapter_id: UUID
    provider_id: str
    source_page_id: str
    position: int
    state: DownloadPageState = DownloadPageState.QUEUED
    attempts: int = 0
    byte_size: int | None = None
    sha256: str | None = None
    original_path: Path | None = None
    temporary_path: Path | None = None
    next_attempt_at: datetime | None = None
    error_code: str | None = None
    duplicate_content: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.source_page_id.strip():
            raise DomainValidationError("A página precisa de identidades estáveis.")
        if self.position < 0 or self.attempts < 0:
            raise DomainValidationError("A posição e as tentativas precisam ser válidas.")
        if self.byte_size is not None and self.byte_size < 0:
            raise DomainValidationError("O tamanho da página não pode ser negativo.")
        if self.next_attempt_at is not None and self.next_attempt_at.utcoffset() is None:
            raise DomainValidationError("O próximo retry precisa conter fuso horário.")
        if self.state is DownloadPageState.COMPLETE and not all(
            (self.sha256, self.original_path, self.byte_size is not None)
        ):
            raise DomainValidationError("Uma página completa precisa de arquivo e checksum.")
