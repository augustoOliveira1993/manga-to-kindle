"""Persistência transacional da fila e identidade estável de páginas."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from manga_to_kindle.application.downloads.errors import (
    DownloadIdentityConflict,
    DownloadRecordNotFound,
    DownloadSelectionInvalid,
    DuplicateActiveDownload,
)
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.download_job import DownloadJob, DownloadState
from manga_to_kindle.domain.downloads import (
    DownloadChapterProgress,
    DownloadChapterState,
    DownloadPage,
    DownloadPageState,
)
from manga_to_kindle.domain.providers import ProviderPageReference
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    ChapterRecord,
    DownloadChapterRecord,
    DownloadJobRecord,
    DownloadPageRecord,
    MangaRecord,
    PageRecord,
)

type ChapterPageReferences = tuple[Chapter, tuple[ProviderPageReference, ...]]

_DOWNLOAD_COMPLETION_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class DownloadQueueSnapshot:
    job: DownloadJob
    chapter_ids: tuple[UUID, ...]
    chapter_progress: tuple[DownloadChapterProgress, ...]
    pages: tuple[DownloadPage, ...]


class DownloadRepository:
    def __init__(self, database: SQLiteDatabase, managed_root: Path) -> None:
        self._database = database
        self._managed_root = managed_root.expanduser().resolve()

    def enqueue(
        self,
        *,
        manga_id: UUID,
        provider_id: str,
        chapter_pages: Sequence[ChapterPageReferences],
        policy_snapshot: Mapping[str, object],
    ) -> DownloadQueueSnapshot:
        ordered = _validate_chapter_pages(manga_id, chapter_pages)
        selected_chapters = tuple(chapter.id for chapter, _ in ordered)
        selected_page_keys = frozenset(
            (chapter.id, reference.source_id)
            for chapter, references in ordered
            for reference in references
        )
        total = len(selected_page_keys)
        if total == 0:
            raise DownloadSelectionInvalid("A seleção não contém páginas para baixar.")

        job_id: UUID
        with self._database.unit_of_work() as session:
            manga = session.get(MangaRecord, manga_id)
            if manga is None or manga.provider_id != provider_id:
                raise DownloadIdentityConflict("O catálogo não pertence ao provedor selecionado.")
            for chapter, _ in ordered:
                record = session.get(ChapterRecord, chapter.id)
                if record is None or record.manga_id != manga_id:
                    raise DownloadIdentityConflict("Um capítulo não pertence ao catálogo atual.")

            self._reject_duplicate_active(
                session,
                manga_id=manga_id,
                provider_id=provider_id,
                chapter_ids=frozenset(selected_chapters),
                page_keys=selected_page_keys,
            )
            job_id = uuid4()
            job_record = DownloadJobRecord(
                id=job_id,
                manga_id=manga_id,
                state=DownloadState.QUEUED.value,
                progress=0,
                total=total,
                cancel_requested=False,
                provider_id=provider_id,
                policy_snapshot=dict(policy_snapshot),
                error_code=None,
            )
            session.add(job_record)
            session.flush()

            for chapter_position, (chapter, references) in enumerate(ordered):
                reusable = self._reusable_pages(session, provider_id, chapter.id)
                complete_count = 0
                chapter_record = DownloadChapterRecord(
                    job_id=job_id,
                    chapter_id=chapter.id,
                    position=chapter_position,
                    state="queued",
                    page_total=len(references),
                    page_completed=0,
                )
                session.add(chapter_record)
                for reference in references:
                    existing = reusable.get(reference.source_id)
                    if existing is not None and _matches_managed_file(
                        Path(existing.original_path or ""),
                        existing.sha256,
                        self._managed_root,
                    ):
                        state = DownloadPageState.COMPLETE
                        original_path = existing.original_path
                        sha256 = existing.sha256
                        byte_size = existing.byte_size
                        complete_count += 1
                        page_uuid = _stable_page_uuid(provider_id, chapter.id, reference.source_id)
                        existing_page = session.get(PageRecord, page_uuid)
                        if existing_page is None:
                            session.add(
                                PageRecord(
                                    id=page_uuid,
                                    chapter_id=chapter.id,
                                    position=reference.position,
                                    original_path=original_path or "",
                                )
                            )
                        elif (
                            existing_page.position != reference.position
                            or existing_page.original_path != original_path
                        ):
                            raise DownloadIdentityConflict(
                                "A identidade da página conflita com o arquivo local existente."
                            )
                    else:
                        state = DownloadPageState.QUEUED
                        original_path = None
                        sha256 = None
                        byte_size = None
                    session.add(
                        DownloadPageRecord(
                            job_id=job_id,
                            chapter_id=chapter.id,
                            provider_id=provider_id,
                            provider_page_id=reference.source_id,
                            position=reference.position,
                            state=state.value,
                            attempts=0,
                            byte_size=byte_size,
                            sha256=sha256,
                            original_path=original_path,
                            duplicate_content=False,
                        )
                    )
                chapter_record.page_completed = complete_count
                if complete_count == len(references):
                    chapter_record.state = "complete"
                elif complete_count:
                    chapter_record.state = "partial"
            session.flush()
            completed = session.scalar(
                select(func.count()).select_from(DownloadPageRecord).where(
                    DownloadPageRecord.job_id == job_id,
                    DownloadPageRecord.state == DownloadPageState.COMPLETE.value,
                )
            ) or 0
            job_record.progress = completed
            if completed == total:
                job_record.state = DownloadState.SUCCEEDED.value
                job_record.updated_at = datetime.now(UTC)

        snapshot = self.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho criado não foi encontrado.")
        return snapshot

    def get(self, job_id: UUID) -> DownloadQueueSnapshot | None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadJobRecord, job_id)
            if record is None:
                return None
            chapters = tuple(
                session.scalars(
                    select(DownloadChapterRecord)
                    .where(DownloadChapterRecord.job_id == job_id)
                    .order_by(DownloadChapterRecord.position)
                )
            )
            pages = tuple(
                session.scalars(
                    select(DownloadPageRecord)
                    .join(
                        DownloadChapterRecord,
                        (DownloadChapterRecord.job_id == DownloadPageRecord.job_id)
                        & (DownloadChapterRecord.chapter_id == DownloadPageRecord.chapter_id),
                    )
                    .where(DownloadPageRecord.job_id == job_id)
                    .order_by(DownloadChapterRecord.position, DownloadPageRecord.position)
                )
            )
            job = _domain_job(record)
            return DownloadQueueSnapshot(
                job=job,
                chapter_ids=tuple(chapter.chapter_id for chapter in chapters),
                chapter_progress=tuple(_domain_chapter(chapter) for chapter in chapters),
                pages=tuple(_domain_page(record) for record in pages),
            )

    def list_jobs(self) -> tuple[DownloadJob, ...]:
        with self._database.unit_of_work() as session:
            records = session.scalars(
                select(DownloadJobRecord).order_by(DownloadJobRecord.created_at.desc())
            )
            return tuple(_domain_job(record) for record in records)

    def list_snapshots(self) -> tuple[DownloadQueueSnapshot, ...]:
        with self._database.unit_of_work() as session:
            job_ids = tuple(
                session.scalars(
                    select(DownloadJobRecord.id).order_by(DownloadJobRecord.created_at.desc())
                )
            )
        return tuple(snapshot for job_id in job_ids if (snapshot := self.get(job_id)) is not None)

    def set_job_state(
        self,
        job_id: UUID,
        next_state: DownloadState,
        *,
        error_code: str | None = None,
    ) -> DownloadJob:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadJobRecord, job_id)
            if record is None:
                raise DownloadRecordNotFound("O trabalho não foi encontrado.")
            job = _domain_job(record)
            if job.state is not next_state:
                job = job.transition_to(next_state)
            if next_state is DownloadState.RUNNING:
                job = replace(job, cancel_requested=False, updated_at=datetime.now(UTC))
            record.state = job.state.value
            record.cancel_requested = job.cancel_requested
            record.updated_at = job.updated_at
            record.error_code = _safe_error_code(error_code)
            chapter_state = {
                DownloadState.RUNNING: DownloadChapterState.RUNNING.value,
                DownloadState.PAUSED: DownloadChapterState.PAUSED.value,
                DownloadState.INTERRUPTED: DownloadChapterState.INTERRUPTED.value,
                DownloadState.FAILED: DownloadChapterState.FAILED.value,
                DownloadState.CANCELLED: DownloadChapterState.CANCELLED.value,
                DownloadState.SUCCEEDED: DownloadChapterState.COMPLETE.value,
            }.get(next_state)
            if chapter_state is not None:
                chapters = session.scalars(
                    select(DownloadChapterRecord).where(
                        DownloadChapterRecord.job_id == job_id,
                        DownloadChapterRecord.state != DownloadChapterState.COMPLETE.value,
                    )
                )
                for chapter in chapters:
                    chapter.state = chapter_state
            return job

    def request_cancel(self, job_id: UUID) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadJobRecord, job_id)
            if record is None:
                raise DownloadRecordNotFound("O trabalho não foi encontrado.")
            job = _domain_job(record)
            updated = job.request_cancellation()
            record.cancel_requested = updated.cancel_requested
            record.updated_at = updated.updated_at

    def begin_page_attempt(self, job_id: UUID, page_id: UUID) -> DownloadPage:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            if record.state not in {
                DownloadPageState.QUEUED.value,
                DownloadPageState.INTERRUPTED.value,
                DownloadPageState.WAITING_RETRY.value,
            }:
                raise DownloadIdentityConflict("A página não pode iniciar outra tentativa.")
            record.state = DownloadPageState.RUNNING.value
            record.attempts += 1
            record.next_attempt_at = None
            record.error_code = None
            return _domain_page(record)

    def set_page_temporary_path(self, job_id: UUID, page_id: UUID, path: Path) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            record.temporary_path = path.as_posix()

    def mark_page_staging(
        self,
        job_id: UUID,
        page_id: UUID,
        *,
        temporary_path: Path,
        final_path: Path,
        byte_size: int,
        sha256: str,
    ) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            record.state = DownloadPageState.STAGING.value
            record.temporary_path = temporary_path.as_posix()
            record.original_path = final_path.as_posix()
            record.byte_size = byte_size
            record.sha256 = sha256

    def complete_page(self, job_id: UUID, page_id: UUID) -> DownloadPage:
        with _DOWNLOAD_COMPLETION_LOCK:
            return self._complete_page_locked(job_id, page_id)

    def _complete_page_locked(self, job_id: UUID, page_id: UUID) -> DownloadPage:
        with self._database.unit_of_work() as session:
            page_record = session.get(DownloadPageRecord, page_id)
            if page_record is None or page_record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            job_record = session.get(DownloadJobRecord, job_id)
            if job_record is None or job_record.provider_id is None:
                raise DownloadIdentityConflict("O trabalho não tem provedor associado.")
            if (
                page_record.state != DownloadPageState.STAGING.value
                or page_record.original_path is None
                or page_record.sha256 is None
                or page_record.byte_size is None
            ):
                raise DownloadIdentityConflict("A página não está pronta para finalização.")
            local_id = _stable_page_uuid(
                job_record.provider_id,
                page_record.chapter_id,
                page_record.provider_page_id,
            )
            existing = session.get(PageRecord, local_id)
            if existing is not None and (
                existing.chapter_id != page_record.chapter_id
                or existing.position != page_record.position
                or existing.original_path != page_record.original_path
            ):
                raise DownloadIdentityConflict(
                    "O arquivo local da página já possui outra identidade."
                )
            position_owner = session.scalar(
                select(PageRecord).where(
                    PageRecord.chapter_id == page_record.chapter_id,
                    PageRecord.position == page_record.position,
                )
            )
            if position_owner is not None and position_owner.id != local_id:
                raise DownloadIdentityConflict("A posição já pertence a outra página local.")
            if existing is None:
                session.add(
                    PageRecord(
                        id=local_id,
                        chapter_id=page_record.chapter_id,
                        position=page_record.position,
                        original_path=page_record.original_path,
                    )
                )
            duplicate = session.scalar(
                select(DownloadPageRecord.id)
                .join(DownloadJobRecord, DownloadJobRecord.id == DownloadPageRecord.job_id)
                .where(
                    DownloadJobRecord.provider_id == job_record.provider_id,
                    DownloadPageRecord.sha256 == page_record.sha256,
                    DownloadPageRecord.state == DownloadPageState.COMPLETE.value,
                    DownloadPageRecord.id != page_id,
                )
                .limit(1)
            )
            page_record.state = DownloadPageState.COMPLETE.value
            page_record.temporary_path = None
            page_record.duplicate_content = duplicate is not None
            chapter_record = session.get(
                DownloadChapterRecord, (job_id, page_record.chapter_id)
            )
            if chapter_record is None:
                raise DownloadIdentityConflict("O trabalho não contém o capítulo da página.")
            chapter_record.page_completed += 1
            if chapter_record.page_total == chapter_record.page_completed:
                chapter_record.state = DownloadChapterState.COMPLETE.value
            else:
                chapter_record.state = DownloadChapterState.RUNNING.value
            job_record.progress += 1
            if job_record.total is not None and job_record.progress == job_record.total:
                current = _domain_job(job_record)
                done = current.transition_to(DownloadState.SUCCEEDED)
                job_record.state = done.state.value
                job_record.updated_at = done.updated_at
            return _domain_page(page_record)

    def schedule_retry(
        self,
        job_id: UUID,
        page_id: UUID,
        *,
        next_attempt_at: datetime,
        error_code: str,
    ) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            if next_attempt_at.utcoffset() is None:
                raise DownloadSelectionInvalid("O prazo de retry precisa conter fuso horário.")
            record.state = DownloadPageState.WAITING_RETRY.value
            record.next_attempt_at = next_attempt_at.astimezone(UTC)
            record.error_code = _safe_error_code(error_code)

    def fail_page(self, job_id: UUID, page_id: UUID, *, error_code: str) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            record.state = DownloadPageState.FAILED.value
            record.error_code = _safe_error_code(error_code)
            record.temporary_path = None

    def interrupt_page(self, job_id: UUID, page_id: UUID) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(DownloadPageRecord, page_id)
            if record is None or record.job_id != job_id:
                raise DownloadRecordNotFound("A página da fila não foi encontrada.")
            if record.state != DownloadPageState.COMPLETE.value:
                record.state = DownloadPageState.INTERRUPTED.value
                record.next_attempt_at = None
                record.temporary_path = None

    def recover_interrupted(self) -> tuple[DownloadQueueSnapshot, ...]:
        """Marca somente o que estava rodando; trabalhos enfileirados nunca iniciam sozinhos."""
        with self._database.unit_of_work() as session:
            running = tuple(
                session.scalars(
                    select(DownloadJobRecord).where(
                        DownloadJobRecord.state == DownloadState.RUNNING.value
                    )
                )
            )
            active_pages = tuple(
                session.scalars(
                    select(DownloadPageRecord).where(
                        DownloadPageRecord.state.in_(
                            (
                                DownloadPageState.RUNNING.value,
                                DownloadPageState.STAGING.value,
                            )
                        )
                    )
                )
            )
            job_ids = tuple(
                dict.fromkeys(
                    [record.id for record in running]
                    + [page.job_id for page in active_pages]
                )
            )
            for record in running:
                record.state = DownloadState.INTERRUPTED.value
                record.updated_at = datetime.now(UTC)
                chapter_records = session.scalars(
                    select(DownloadChapterRecord).where(
                        DownloadChapterRecord.job_id == record.id,
                        DownloadChapterRecord.state != DownloadChapterState.COMPLETE.value,
                    )
                )
                for chapter in chapter_records:
                    chapter.state = DownloadChapterState.INTERRUPTED.value
            for page in active_pages:
                if page.state == DownloadPageState.RUNNING.value:
                    page.state = DownloadPageState.INTERRUPTED.value
        return tuple(snapshot for job_id in job_ids if (snapshot := self.get(job_id)) is not None)

    def _reject_duplicate_active(
        self,
        session: Session,
        *,
        manga_id: UUID,
        provider_id: str,
        chapter_ids: frozenset[UUID],
        page_keys: frozenset[tuple[UUID, str]],
    ) -> None:
        records = session.scalars(
            select(DownloadJobRecord).where(
                DownloadJobRecord.manga_id == manga_id,
                DownloadJobRecord.provider_id == provider_id,
                DownloadJobRecord.state.in_(
                    (
                        DownloadState.QUEUED.value,
                        DownloadState.RUNNING.value,
                        DownloadState.PAUSED.value,
                        DownloadState.INTERRUPTED.value,
                    )
                ),
            )
        )
        for record in records:
            chapters = frozenset(
                session.scalars(
                    select(DownloadChapterRecord.chapter_id).where(
                        DownloadChapterRecord.job_id == record.id
                    )
                )
            )
            pages = frozenset(
                (chapter_id, page_id)
                for chapter_id, page_id in session.execute(
                    select(
                        DownloadPageRecord.chapter_id,
                        DownloadPageRecord.provider_page_id,
                    ).where(DownloadPageRecord.job_id == record.id)
                )
            )
            if chapters == chapter_ids and pages == page_keys:
                raise DuplicateActiveDownload("A mesma seleção já está ativa na fila.")

    def _reusable_pages(
        self,
        session: Session,
        provider_id: str,
        chapter_id: UUID,
    ) -> dict[str, DownloadPageRecord]:
        rows = session.scalars(
            select(DownloadPageRecord)
            .join(DownloadJobRecord, DownloadJobRecord.id == DownloadPageRecord.job_id)
            .where(
                DownloadJobRecord.provider_id == provider_id,
                DownloadPageRecord.chapter_id == chapter_id,
                DownloadPageRecord.state == DownloadPageState.COMPLETE.value,
            )
            .order_by(DownloadJobRecord.updated_at.desc())
        )
        result: dict[str, DownloadPageRecord] = {}
        for row in rows:
            result.setdefault(row.provider_page_id, row)
        return result


def _validate_chapter_pages(
    manga_id: UUID,
    chapter_pages: Sequence[ChapterPageReferences],
) -> tuple[ChapterPageReferences, ...]:
    if not chapter_pages:
        raise DownloadSelectionInvalid("Selecione pelo menos um capítulo.")
    if len({chapter.id for chapter, _ in chapter_pages}) != len(chapter_pages):
        raise DownloadSelectionInvalid("A seleção contém capítulo repetido.")
    if any(chapter.manga_id != manga_id for chapter, _ in chapter_pages):
        raise DownloadSelectionInvalid("Todos os capítulos devem pertencer ao mesmo mangá.")
    ordered = tuple(sorted(chapter_pages, key=lambda item: item[0].position))
    for _chapter, references in ordered:
        if not references:
            raise DownloadSelectionInvalid("Um capítulo selecionado não contém páginas.")
        if any(reference.simulated for reference in references):
            raise DownloadSelectionInvalid("Referências de demonstração não podem ser baixadas.")
        if len({reference.source_id for reference in references}) != len(references):
            raise DownloadSelectionInvalid("O catálogo retornou IDs de página repetidos.")
        if len({reference.position for reference in references}) != len(references):
            raise DownloadSelectionInvalid("O catálogo retornou posições de página repetidas.")
    return tuple(
        (chapter, tuple(sorted(references, key=lambda reference: reference.position)))
        for chapter, references in ordered
    )


def _domain_job(record: DownloadJobRecord) -> DownloadJob:
    created_at = _utc(record.created_at)
    updated_at = _utc(record.updated_at)
    return DownloadJob(
        id=record.id,
        target_manga_id=record.manga_id,
        target_chapter_id=record.chapter_id,
        state=DownloadState(record.state),
        progress=record.progress,
        total=record.total,
        cancel_requested=record.cancel_requested,
        provider_id=record.provider_id,
        created_at=created_at,
        updated_at=updated_at,
    )


def _domain_chapter(record: DownloadChapterRecord) -> DownloadChapterProgress:
    try:
        state = DownloadChapterState(record.state)
    except ValueError:
        raise DownloadIdentityConflict("O estado persistido de um capítulo é inválido.") from None
    return DownloadChapterProgress(
        chapter_id=record.chapter_id,
        position=record.position,
        state=state,
        page_total=record.page_total,
        page_completed=record.page_completed,
    )


def _domain_page(record: DownloadPageRecord) -> DownloadPage:
    return DownloadPage(
        id=record.id,
        job_id=record.job_id,
        chapter_id=record.chapter_id,
        provider_id=record.provider_id,
        source_page_id=record.provider_page_id,
        position=record.position,
        state=DownloadPageState(record.state),
        attempts=record.attempts,
        byte_size=record.byte_size,
        sha256=record.sha256,
        original_path=Path(record.original_path) if record.original_path else None,
        temporary_path=Path(record.temporary_path) if record.temporary_path else None,
        next_attempt_at=_utc(record.next_attempt_at) if record.next_attempt_at else None,
        error_code=record.error_code,
        duplicate_content=record.duplicate_content,
    )


def _stable_page_uuid(provider_id: str, chapter_id: UUID, source_page_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{provider_id}\0{chapter_id}\0{source_page_id}")


def _matches_managed_file(path: Path, checksum: str | None, root: Path) -> bool:
    if not checksum:
        return False
    try:
        resolved_root = root.resolve()
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
        if not resolved_path.is_file():
            return False
        digest = hashlib.sha256()
        with resolved_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(64 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == checksum
    except (OSError, RuntimeError, ValueError):
        return False


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _safe_error_code(value: str | None) -> str | None:
    if value is None:
        return None
    import re

    return value if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value) else "DOWNLOAD_FAILED"
