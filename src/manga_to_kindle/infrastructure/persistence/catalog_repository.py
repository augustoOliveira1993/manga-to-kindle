"""Persistência transacional de um único snapshot atual por mangá."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    CatalogMembershipRecord,
    ChapterRecord,
    MangaRecord,
)


class CatalogPersistenceError(RuntimeError):
    code = "CATALOG_PERSISTENCE_FAILED"


class CatalogIdentityConflict(CatalogPersistenceError):
    code = "CATALOG_IDENTITY_CONFLICT"


class CatalogRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def replace(self, snapshot: CatalogSnapshot) -> None:
        with self._database.unit_of_work() as session:
            manga = session.get(MangaRecord, snapshot.manga.id)
            if manga is None:
                manga = MangaRecord(id=snapshot.manga.id, title=snapshot.manga.title)
                session.add(manga)
                session.flush()
            elif manga.provider_id not in {None, snapshot.provider_id}:
                raise CatalogIdentityConflict("O ID do mangá pertence a outro provedor.")
            elif manga.provider_id is not None and manga.source_ref != snapshot.source_id:
                raise CatalogIdentityConflict(
                    "O ID do mangá aponta para outra identidade de origem."
                )

            manga.title = snapshot.manga.title
            manga.source_ref = snapshot.source_id
            manga.provider_id = snapshot.provider_id
            manga.author = snapshot.manga.author
            manga.cover_path = (
                snapshot.manga.cover_path.as_posix()
                if snapshot.manga.cover_path is not None
                else None
            )
            manga.language = snapshot.manga.language
            manga.simulated = snapshot.simulated
            manga.updated_at = snapshot.updated_at

            next_storage_position = (
                session.scalar(
                    select(func.max(ChapterRecord.position)).where(
                        ChapterRecord.manga_id == snapshot.manga.id
                    )
                )
                or -1
            ) + 1
            for chapter in snapshot.chapters:
                record = session.get(ChapterRecord, chapter.id)
                if record is None:
                    record = ChapterRecord(
                        id=chapter.id,
                        manga_id=snapshot.manga.id,
                        position=next_storage_position,
                    )
                    next_storage_position += 1
                    session.add(record)
                elif record.manga_id != snapshot.manga.id:
                    raise CatalogIdentityConflict("O ID do capítulo pertence a outro mangá.")
                record.title = chapter.title
                record.number = str(chapter.number) if chapter.number is not None else None
                record.volume = str(chapter.volume) if chapter.volume is not None else None
                record.available = chapter.available

            session.flush()
            session.execute(
                delete(CatalogMembershipRecord).where(
                    CatalogMembershipRecord.manga_id == snapshot.manga.id
                )
            )
            session.add_all(
                CatalogMembershipRecord(
                    manga_id=snapshot.manga.id,
                    chapter_id=chapter.id,
                    position=position,
                    source_order=chapter.source_order,
                )
                for position, chapter in enumerate(snapshot.chapters)
            )

    def get(self, manga_id: UUID) -> CatalogSnapshot | None:
        with self._database.unit_of_work() as session:
            manga_record = session.get(MangaRecord, manga_id)
            if manga_record is None or manga_record.provider_id is None:
                return None
            memberships = tuple(
                session.scalars(
                    select(CatalogMembershipRecord)
                    .where(CatalogMembershipRecord.manga_id == manga_id)
                    .order_by(CatalogMembershipRecord.position)
                )
            )
            chapters: list[Chapter] = []
            for membership in memberships:
                record = session.get(ChapterRecord, membership.chapter_id)
                if record is None:
                    raise CatalogPersistenceError("O catálogo referencia um capítulo ausente.")
                try:
                    chapters.append(
                        Chapter(
                            manga_id=manga_id,
                            id=record.id,
                            position=membership.position,
                            title=record.title,
                            number=Decimal(record.number) if record.number is not None else None,
                            volume=Decimal(record.volume) if record.volume is not None else None,
                            available=record.available,
                            source_order=membership.source_order,
                        )
                    )
                except (DomainValidationError, ArithmeticError):
                    raise CatalogPersistenceError(
                        "Os metadados salvos do catálogo são inválidos."
                    ) from None
            manga = Manga(
                id=manga_record.id,
                title=manga_record.title,
                source_ref=manga_record.source_ref,
                author=manga_record.author,
                cover_path=Path(manga_record.cover_path) if manga_record.cover_path else None,
                language=manga_record.language,
                chapters=tuple(chapters),
            )
            updated_at = manga_record.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            else:
                updated_at = updated_at.astimezone(UTC)
            return CatalogSnapshot(
                provider_id=manga_record.provider_id,
                source_id=manga_record.source_ref or manga_record.provider_id,
                manga=manga,
                updated_at=updated_at,
                simulated=manga_record.simulated,
            )
