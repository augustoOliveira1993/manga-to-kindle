"""Persistência local e transacional de histórico/avisos F010."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.updates import (
    ChapterNotice,
    UpdateCheck,
    UpdateCheckStatus,
    UpdateMangaStatus,
    UpdatePreference,
)
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    CatalogMembershipRecord,
    ChapterNoticeRecord,
    ChapterRecord,
    MangaRecord,
    UpdateCheckRecord,
    UpdatePreferenceRecord,
)


class UpdatePersistenceError(RuntimeError):
    code = "UPDATE_PERSISTENCE_FAILED"


class UpdateRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def get_preference(self, manga_id: UUID) -> UpdatePreference:
        with self._database.unit_of_work() as session:
            record = session.get(UpdatePreferenceRecord, manga_id)
            if record is None:
                return UpdatePreference(manga_id=manga_id)
            return UpdatePreference(
                manga_id=record.manga_id,
                enabled=record.enabled,
                interval_seconds=record.interval_seconds,
                notifications_enabled=record.notifications_enabled,
                updated_at=_utc(record.updated_at),
            )

    def save_preference(self, preference: UpdatePreference) -> UpdatePreference:
        now = _utc(preference.updated_at or datetime.now(UTC))
        with self._database.unit_of_work() as session:
            if session.get(MangaRecord, preference.manga_id) is None:
                raise UpdatePersistenceError("O mangá não existe no catálogo local.")
            record = session.get(UpdatePreferenceRecord, preference.manga_id)
            if record is None:
                record = UpdatePreferenceRecord(manga_id=preference.manga_id)
                session.add(record)
            record.enabled = preference.enabled
            record.interval_seconds = preference.interval_seconds
            record.notifications_enabled = preference.notifications_enabled
            record.updated_at = now
        return UpdatePreference(
            manga_id=preference.manga_id,
            enabled=preference.enabled,
            interval_seconds=preference.interval_seconds,
            notifications_enabled=preference.notifications_enabled,
            updated_at=now,
        )

    def latest_check(self, manga_id: UUID) -> UpdateCheck | None:
        with self._database.unit_of_work() as session:
            record = session.scalar(
                select(UpdateCheckRecord)
                .where(UpdateCheckRecord.manga_id == manga_id)
                .order_by(UpdateCheckRecord.started_at.desc(), UpdateCheckRecord.id.desc())
                .limit(1)
            )
            return _check_from_record(record) if record is not None else None

    def latest_provider_check(self, provider_id: str) -> UpdateCheck | None:
        with self._database.unit_of_work() as session:
            record = session.scalar(
                select(UpdateCheckRecord)
                .where(UpdateCheckRecord.provider_id == provider_id)
                .order_by(UpdateCheckRecord.started_at.desc(), UpdateCheckRecord.id.desc())
                .limit(1)
            )
            return _check_from_record(record) if record is not None else None

    def has_successful_check(self, manga_id: UUID) -> bool:
        with self._database.unit_of_work() as session:
            return bool(
                session.scalar(
                    select(func.count())
                    .select_from(UpdateCheckRecord)
                    .where(
                        UpdateCheckRecord.manga_id == manga_id,
                        UpdateCheckRecord.status == UpdateCheckStatus.SUCCEEDED.value,
                    )
                )
            )

    def record_check(self, check: UpdateCheck) -> None:
        if check.status is UpdateCheckStatus.SUCCEEDED:
            raise ValueError("Consultas bem-sucedidas devem ser salvas com o snapshot.")
        with self._database.unit_of_work() as session:
            session.add(_check_record(check))

    def commit_snapshot(
        self,
        snapshot: CatalogSnapshot,
        check: UpdateCheck,
        new_source_chapter_ids: tuple[str, ...],
    ) -> tuple[ChapterNotice, ...]:
        if (
            snapshot.simulated
            or check.status is not UpdateCheckStatus.SUCCEEDED
            or check.manga_id != snapshot.manga.id
            or check.provider_id != snapshot.provider_id
            or check.chapter_count != len(snapshot.chapters)
            or check.new_chapter_count != len(set(new_source_chapter_ids))
        ):
            raise ValueError("O histórico de atualização não corresponde ao snapshot completo.")
        now = _utc(check.finished_at or datetime.now(UTC))
        new_ids = tuple(dict.fromkeys(new_source_chapter_ids))
        created: list[ChapterNotice] = []
        with self._database.unit_of_work() as session:
            preference = session.get(UpdatePreferenceRecord, snapshot.manga.id)
            CatalogRepository.replace_in_session(session, snapshot)
            session.add(_check_record(check))
            session.flush()
            if preference is not None and not preference.notifications_enabled:
                return ()
            chapters_by_source = {
                source_id: chapter_id
                for source_id, chapter_id in session.execute(
                    select(
                        ChapterRecord.source_chapter_id,
                        ChapterRecord.id,
                    ).where(ChapterRecord.manga_id == snapshot.manga.id)
                )
                if source_id is not None
            }
            for source_id in new_ids:
                chapter_id = chapters_by_source.get(source_id)
                if chapter_id is None:
                    raise UpdatePersistenceError("O snapshot não contém uma identidade anunciada.")
                chapter_record = session.get(ChapterRecord, chapter_id)
                if chapter_record is None:
                    raise UpdatePersistenceError("O capítulo anunciado não existe no catálogo.")
                existing = session.scalar(
                    select(ChapterNoticeRecord).where(
                        ChapterNoticeRecord.manga_id == snapshot.manga.id,
                        ChapterNoticeRecord.provider_id == snapshot.provider_id,
                        ChapterNoticeRecord.source_chapter_id == source_id,
                    )
                )
                if existing is not None:
                    continue
                notice = ChapterNotice(
                    manga_id=snapshot.manga.id,
                    provider_id=snapshot.provider_id,
                    source_chapter_id=source_id,
                    chapter_title_snapshot=(
                        chapter_record.title
                        or (
                            f"Capítulo {chapter_record.number}"
                            if chapter_record.number is not None
                            else "Capítulo especial"
                        )
                    ),
                    chapter_id=chapter_id,
                    check_id=check.id,
                    created_at=now,
                )
                session.add(_notice_record(notice))
                created.append(notice)
        return tuple(created)

    def list_notices(
        self, manga_id: UUID, *, unread_only: bool = False
    ) -> tuple[ChapterNotice, ...]:
        with self._database.unit_of_work() as session:
            query = select(ChapterNoticeRecord).where(ChapterNoticeRecord.manga_id == manga_id)
            if unread_only:
                query = query.where(ChapterNoticeRecord.read_at.is_(None))
            records = tuple(session.scalars(query.order_by(ChapterNoticeRecord.created_at.desc())))
            return tuple(_notice_from_record(record) for record in records)

    def mark_notice_read(self, notice_id: UUID, read_at: datetime | None = None) -> bool:
        with self._database.unit_of_work() as session:
            record = session.get(ChapterNoticeRecord, notice_id)
            if record is None:
                return False
            record.read_at = _utc(read_at or datetime.now(UTC))
            return True

    def list_statuses(self) -> tuple[UpdateMangaStatus, ...]:
        with self._database.unit_of_work() as session:
            mangas = tuple(
                session.scalars(select(MangaRecord).order_by(MangaRecord.title.collate("NOCASE")))
            )
            result: list[UpdateMangaStatus] = []
            for manga in mangas:
                preference_record = session.get(UpdatePreferenceRecord, manga.id)
                preference = (
                    UpdatePreference(
                        manga_id=manga.id,
                        enabled=preference_record.enabled,
                        interval_seconds=preference_record.interval_seconds,
                        notifications_enabled=preference_record.notifications_enabled,
                        updated_at=_utc(preference_record.updated_at),
                    )
                    if preference_record is not None
                    else UpdatePreference(manga_id=manga.id)
                )
                count = (
                    session.scalar(
                        select(func.count())
                        .select_from(CatalogMembershipRecord)
                        .where(CatalogMembershipRecord.manga_id == manga.id)
                    )
                    or 0
                )
                latest = session.scalar(
                    select(UpdateCheckRecord)
                    .where(UpdateCheckRecord.manga_id == manga.id)
                    .order_by(UpdateCheckRecord.started_at.desc(), UpdateCheckRecord.id.desc())
                    .limit(1)
                )
                unread_count = (
                    session.scalar(
                        select(func.count())
                        .select_from(ChapterNoticeRecord)
                        .where(
                            ChapterNoticeRecord.manga_id == manga.id,
                            ChapterNoticeRecord.read_at.is_(None),
                        )
                    )
                    or 0
                )
                result.append(
                    UpdateMangaStatus(
                        manga_id=manga.id,
                        title=manga.title,
                        provider_id=manga.provider_id,
                        simulated=manga.simulated,
                        chapter_count=int(count),
                        preference=preference,
                        last_check=_check_from_record(latest) if latest is not None else None,
                        unread_notice_count=int(unread_count),
                    )
                )
            return tuple(result)


def _check_record(check: UpdateCheck) -> UpdateCheckRecord:
    return UpdateCheckRecord(
        id=check.id,
        manga_id=check.manga_id,
        provider_id=check.provider_id,
        started_at=_utc(check.started_at),
        finished_at=_utc(check.finished_at) if check.finished_at is not None else None,
        status=check.status.value,
        chapter_count=check.chapter_count,
        new_chapter_count=check.new_chapter_count,
        safe_error_code=check.safe_error_code,
        retry_after_at=_utc(check.retry_after_at) if check.retry_after_at is not None else None,
        policy_fingerprint=check.policy_fingerprint,
    )


def _check_from_record(record: UpdateCheckRecord) -> UpdateCheck:
    try:
        return UpdateCheck(
            id=record.id,
            manga_id=record.manga_id,
            provider_id=record.provider_id,
            started_at=_utc(record.started_at),
            finished_at=_utc(record.finished_at) if record.finished_at is not None else None,
            status=UpdateCheckStatus(record.status),
            chapter_count=record.chapter_count,
            new_chapter_count=record.new_chapter_count,
            safe_error_code=record.safe_error_code,
            retry_after_at=(
                _utc(record.retry_after_at) if record.retry_after_at is not None else None
            ),
            policy_fingerprint=record.policy_fingerprint,
        )
    except (TypeError, ValueError):
        raise UpdatePersistenceError("O histórico de atualização salvo é inválido.") from None


def _notice_record(notice: ChapterNotice) -> ChapterNoticeRecord:
    return ChapterNoticeRecord(
        id=notice.id,
        manga_id=notice.manga_id,
        provider_id=notice.provider_id,
        source_chapter_id=notice.source_chapter_id,
        chapter_title_snapshot=notice.chapter_title_snapshot,
        chapter_id=notice.chapter_id,
        check_id=notice.check_id,
        created_at=_utc(notice.created_at),
        read_at=_utc(notice.read_at) if notice.read_at is not None else None,
    )


def _notice_from_record(record: ChapterNoticeRecord) -> ChapterNotice:
    try:
        return ChapterNotice(
            id=record.id,
            manga_id=record.manga_id,
            provider_id=record.provider_id,
            source_chapter_id=record.source_chapter_id,
            chapter_title_snapshot=record.chapter_title_snapshot,
            chapter_id=record.chapter_id,
            check_id=record.check_id,
            created_at=_utc(record.created_at),
            read_at=_utc(record.read_at) if record.read_at is not None else None,
        )
    except (TypeError, ValueError):
        raise UpdatePersistenceError("Uma notificação local salva é inválida.") from None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
