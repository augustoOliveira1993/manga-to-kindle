"""Contratos locais de histórico, preferências e novidades do catálogo."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.chapter_ordering import order_chapters
from manga_to_kindle.domain.errors import DomainValidationError


class UpdateCheckStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class UpdatePreference:
    manga_id: UUID
    enabled: bool = False
    interval_seconds: int | None = None
    notifications_enabled: bool = True
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool or type(self.notifications_enabled) is not bool:
            raise DomainValidationError("As preferências de atualização precisam ser booleanas.")
        if self.interval_seconds is not None and (
            type(self.interval_seconds) is not int or self.interval_seconds < 1
        ):
            raise DomainValidationError("O intervalo escolhido precisa ser positivo.")
        if self.enabled and self.interval_seconds is None:
            raise DomainValidationError("Ativar monitoramento exige um intervalo escolhido.")
        if self.updated_at is not None and not _is_aware(self.updated_at):
            raise DomainValidationError("A data da preferência precisa ter fuso horário.")


@dataclass(frozen=True, slots=True)
class UpdateCheck:
    manga_id: UUID
    provider_id: str
    started_at: datetime
    status: UpdateCheckStatus
    id: UUID = field(default_factory=uuid4)
    finished_at: datetime | None = None
    chapter_count: int = 0
    new_chapter_count: int = 0
    safe_error_code: str | None = None
    retry_after_at: datetime | None = None
    policy_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, UpdateCheckStatus):
            raise DomainValidationError("O estado da consulta de atualização é inválido.")
        if not self.provider_id.strip() or not _is_aware(self.started_at):
            raise DomainValidationError(
                "A consulta precisa identificar provedor e horário válidos."
            )
        if self.finished_at is not None and (
            not _is_aware(self.finished_at) or self.finished_at < self.started_at
        ):
            raise DomainValidationError("O término da consulta é inválido.")
        if self.retry_after_at is not None and not _is_aware(self.retry_after_at):
            raise DomainValidationError("A data Retry-After precisa ter fuso horário.")
        if self.policy_fingerprint is not None and re.fullmatch(
            r"[0-9a-f]{64}", self.policy_fingerprint
        ) is None:
            raise DomainValidationError("A impressão da política do provedor é inválida.")
        if type(self.chapter_count) is not int or self.chapter_count < 0:
            raise DomainValidationError("A quantidade de capítulos não pode ser negativa.")
        if (
            type(self.new_chapter_count) is not int
            or self.new_chapter_count < 0
            or self.new_chapter_count > self.chapter_count
        ):
            raise DomainValidationError("A quantidade de novidades está fora do intervalo.")
        if self.safe_error_code is not None and (
            re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", self.safe_error_code) is None
        ):
            raise DomainValidationError("O código de erro persistido precisa ser sanitizado.")
        if self.status is UpdateCheckStatus.SUCCEEDED and (
            self.finished_at is None or self.safe_error_code is not None
        ):
            raise DomainValidationError("Uma consulta concluída precisa terminar sem erro.")
        if self.status is not UpdateCheckStatus.SUCCEEDED and self.new_chapter_count:
            raise DomainValidationError("Uma consulta incompleta não pode registrar novidades.")


@dataclass(frozen=True, slots=True)
class ChapterNotice:
    manga_id: UUID
    provider_id: str
    source_chapter_id: str
    chapter_title_snapshot: str
    chapter_id: UUID
    check_id: UUID
    created_at: datetime
    id: UUID = field(default_factory=uuid4)
    read_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            not self.provider_id.strip()
            or not self.source_chapter_id.strip()
            or len(self.source_chapter_id) > 512
            or not self.chapter_title_snapshot.strip()
            or len(self.chapter_title_snapshot) > 512
            or not _is_aware(self.created_at)
        ):
            raise DomainValidationError("A notificação precisa de identidade estável válida.")
        if self.read_at is not None and not _is_aware(self.read_at):
            raise DomainValidationError("A data de leitura precisa ter fuso horário.")


@dataclass(frozen=True, slots=True)
class UpdateMangaStatus:
    manga_id: UUID
    title: str
    provider_id: str | None
    simulated: bool
    chapter_count: int
    preference: UpdatePreference
    last_check: UpdateCheck | None = None
    unread_notice_count: int = 0

    def __post_init__(self) -> None:
        if not self.title.strip() or self.chapter_count < 0 or self.unread_notice_count < 0:
            raise DomainValidationError("O resumo de atualização do mangá é inválido.")
        if self.preference.manga_id != self.manga_id:
            raise DomainValidationError("A preferência não pertence ao mangá do resumo.")
        if self.last_check is not None and self.last_check.manga_id != self.manga_id:
            raise DomainValidationError("A consulta mais recente não pertence ao mangá do resumo.")


@dataclass(frozen=True, slots=True)
class ChapterReconciliation:
    chapters: tuple[Chapter, ...]
    new_source_chapter_ids: tuple[str, ...]


class UnstableChapterIdentity(DomainValidationError):
    pass


class ConflictingChapterIdentity(DomainValidationError):
    pass


def reconcile_chapters(
    previous: tuple[Chapter, ...],
    incoming: tuple[Chapter, ...],
) -> ChapterReconciliation:
    """Normaliza catálogo completo por ID estável sem usar título/número como chave."""
    old_by_source: dict[str, Chapter] = {}
    old_by_id = {chapter.id: chapter for chapter in previous}
    for chapter in previous:
        source_id = chapter.source_chapter_id
        if source_id is not None:
            if source_id in old_by_source:
                raise ConflictingChapterIdentity("A identidade estável anterior está duplicada.")
            old_by_source[source_id] = chapter

    new_by_source: dict[str, Chapter] = {}
    for chapter in incoming:
        source_id = chapter.source_chapter_id
        if source_id is None:
            raise UnstableChapterIdentity("A resposta omite identidade estável de capítulo.")
        existing_duplicate = new_by_source.get(source_id)
        if existing_duplicate is not None:
            if _chapter_metadata(existing_duplicate) != _chapter_metadata(chapter):
                raise ConflictingChapterIdentity(
                    "Uma identidade repetida possui metadados conflitantes."
                )
            continue
        new_by_source[source_id] = chapter

    new_ids: list[str] = []
    reconciled: list[Chapter] = []
    seen_chapter_ids: set[UUID] = set()
    for source_id, chapter in new_by_source.items():
        old = old_by_source.get(source_id)
        if old is None:
            old = old_by_id.get(chapter.id)
            if old is not None and old.source_chapter_id not in {None, source_id}:
                raise ConflictingChapterIdentity(
                    "O ID local aponta para outra identidade de origem."
                )
        chapter_id = old.id if old is not None else chapter.id
        if chapter_id in seen_chapter_ids:
            raise ConflictingChapterIdentity("O catálogo repete um ID local de capítulo.")
        seen_chapter_ids.add(chapter_id)
        if old is None:
            new_ids.append(source_id)
        reconciled.append(replace(chapter, id=chapter_id))

    ordered = order_chapters(tuple(reconciled))
    positioned = tuple(replace(chapter, position=index) for index, chapter in enumerate(ordered))
    return ChapterReconciliation(positioned, tuple(new_ids))


def _chapter_metadata(chapter: Chapter) -> tuple[object, ...]:
    return (
        chapter.title,
        chapter.number,
        chapter.volume,
        chapter.available,
        chapter.source_order,
    )


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
