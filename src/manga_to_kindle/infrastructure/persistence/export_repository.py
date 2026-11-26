"""Leitura e histórico dos artefatos exportados a partir do banco F001/F006."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.exports import (
    ExportableChapter,
    ExportAsset,
    ExportedArtifact,
    ExportPage,
    ExportPlan,
    ExportSourceChapter,
)
from manga_to_kindle.domain.transfers import ExportTransferArtifact
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    CatalogMembershipRecord,
    ChapterRecord,
    ExportArtifactRecord,
    ExportChapterRecord,
    ExportRecord,
    MangaRecord,
    PageRecord,
    ProcessedPageRecord,
)


class ExportPersistenceError(RuntimeError):
    code = "EXPORT_PERSISTENCE_FAILED"


class ExportSourceUnavailable(ExportPersistenceError):
    code = "EXPORT_SOURCE_UNAVAILABLE"


class ExportRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def list_exportable_chapters(self) -> tuple[ExportableChapter, ...]:
        with self._database.unit_of_work() as session:
            records = session.execute(
                select(ChapterRecord, MangaRecord)
                .join(MangaRecord, MangaRecord.id == ChapterRecord.manga_id)
                .where(MangaRecord.simulated.is_(False))
                .order_by(MangaRecord.title.collate("NOCASE"), ChapterRecord.position)
            ).all()
            choices: list[ExportableChapter] = []
            for chapter, manga in records:
                pages = tuple(
                    session.scalars(
                        select(PageRecord)
                        .where(PageRecord.chapter_id == chapter.id)
                        .order_by(PageRecord.position)
                    )
                )
                if not pages:
                    continue
                processed_by_page = {
                    page.id: tuple(
                        session.scalars(
                            select(ProcessedPageRecord)
                            .where(ProcessedPageRecord.page_id == page.id)
                            .order_by(ProcessedPageRecord.output_order)
                        )
                    )
                    for page in pages
                }
                if any(not processed_by_page[page.id] for page in pages):
                    continue
                if any(
                    record.width != 600 or record.height != 800
                    for processed in processed_by_page.values()
                    for record in processed
                ):
                    continue
                choices.append(
                    ExportableChapter(
                        manga_id=manga.id,
                        chapter_id=chapter.id,
                        manga_title=manga.title,
                        chapter_title=_chapter_title(chapter),
                        page_count=sum(len(items) for items in processed_by_page.values()),
                        language=_optional_text(manga.language),
                        volume=_optional_text(chapter.volume),
                    )
                )
            return tuple(choices)

    def load_sources(self, chapter_ids: tuple[UUID, ...]) -> tuple[ExportSourceChapter, ...]:
        if not chapter_ids or len(chapter_ids) != len(set(chapter_ids)):
            raise ExportSourceUnavailable("A seleção de capítulos está vazia ou repetida.")
        with self._database.unit_of_work() as session:
            records = session.execute(
                select(ChapterRecord, MangaRecord)
                .join(MangaRecord, MangaRecord.id == ChapterRecord.manga_id)
                .where(
                    ChapterRecord.id.in_(chapter_ids),
                    MangaRecord.simulated.is_(False),
                )
            ).all()
            by_id = {chapter.id: (chapter, manga) for chapter, manga in records}
            if set(by_id) != set(chapter_ids):
                raise ExportSourceUnavailable(
                    "Um capítulo não existe, contém dados de demonstração ou foi removido."
                )
            sources: list[ExportSourceChapter] = []
            for chapter_id in chapter_ids:
                chapter_record, manga = by_id[chapter_id]
                page_records = tuple(
                    session.scalars(
                        select(PageRecord)
                        .where(PageRecord.chapter_id == chapter_id)
                        .order_by(PageRecord.position)
                    )
                )
                if not page_records:
                    raise ExportSourceUnavailable("O capítulo selecionado não tem páginas locais.")
                pages: list[ExportPage] = []
                for page in page_records:
                    derivatives = tuple(
                        session.scalars(
                            select(ProcessedPageRecord)
                            .where(ProcessedPageRecord.page_id == page.id)
                            .order_by(ProcessedPageRecord.output_order)
                        )
                    )
                    if not derivatives:
                        raise ExportSourceUnavailable(
                            "Todas as páginas precisam ter um derivado processado em F006."
                        )
                    if any(item.width != 600 or item.height != 800 for item in derivatives):
                        raise ExportSourceUnavailable(
                            "O perfil de saída disponível é de 600 × 800 pixels."
                        )
                    assets = tuple(
                        ExportAsset(
                            path=Path(item.path).expanduser().absolute(),
                            sha256=item.sha256,
                            media_type="image/png",
                            width=item.width,
                            height=item.height,
                            output_order=item.output_order,
                            id=item.id,
                        )
                        for item in derivatives
                    )
                    pages.append(ExportPage(page.id, page.position, assets))
                membership = session.get(CatalogMembershipRecord, (manga.id, chapter_id))
                domain_chapter = Chapter(
                    manga_id=manga.id,
                    id=chapter_record.id,
                    title=_optional_text(chapter_record.title),
                    number=_optional_decimal(chapter_record.number),
                    volume=_optional_decimal(chapter_record.volume),
                    available=chapter_record.available,
                    position=chapter_record.position,
                    source_order=membership.source_order if membership is not None else None,
                )
                sources.append(
                    ExportSourceChapter(
                        chapter=domain_chapter,
                        manga_title=manga.title,
                        pages=tuple(pages),
                        volume=_optional_text(chapter_record.volume),
                        author=_optional_text(manga.author),
                        language=_optional_text(manga.language),
                    )
                )
            return tuple(sources)

    def create(self, plan: ExportPlan) -> None:
        now = datetime.now(UTC)
        snapshot: dict[str, object] = {
            "format": plan.format.value,
            "grouping": plan.grouping.value,
            "direction": plan.direction.value,
            "language": plan.language,
            "profile_id": str(plan.profile.id),
            "profile_name": plan.profile.name,
            "profile": dict(plan.profile.preferences),
            "max_size_bytes": plan.max_size_bytes,
            "package_count": len(plan.packages),
        }
        chapter_ids = tuple(
            chapter_id for package in plan.packages for chapter_id in package.chapter_ids
        )
        ordered_chapters = tuple(dict.fromkeys(chapter_ids))
        with self._database.unit_of_work() as session:
            chapter_rows = session.execute(
                select(ChapterRecord, MangaRecord)
                .join(MangaRecord, MangaRecord.id == ChapterRecord.manga_id)
                .where(ChapterRecord.id.in_(ordered_chapters))
            ).all() if ordered_chapters else ()
            chapter_by_id = {chapter.id: (chapter, manga) for chapter, manga in chapter_rows}
            snapshot["chapter_count"] = len(ordered_chapters)
            snapshot["items"] = [
                {
                    "manga_title": chapter_by_id[chapter_id][1].title,
                    "chapter_title": chapter_by_id[chapter_id][0].title,
                    "chapter_number": chapter_by_id[chapter_id][0].number,
                }
                for chapter_id in ordered_chapters
                if chapter_id in chapter_by_id
            ]
            session.add(
                ExportRecord(
                    id=plan.id,
                    profile_snapshot=snapshot,
                    destination=str(plan.output_directory),
                    state="requested",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add_all(
                ExportChapterRecord(export_id=plan.id, chapter_id=chapter_id, position=position)
                for position, chapter_id in enumerate(ordered_chapters)
            )

    def set_state(self, export_id: UUID, state: str, *, error_code: str | None = None) -> None:
        if state not in {"running", "completed", "failed", "cancelled"}:
            raise ExportPersistenceError("O estado persistido da exportação não é permitido.")
        with self._database.unit_of_work() as session:
            record = session.get(ExportRecord, export_id)
            if record is None:
                raise ExportPersistenceError("A exportação não foi registrada.")
            record.state = state
            record.error_code = error_code
            record.updated_at = datetime.now(UTC)

    def complete(
        self,
        export_id: UUID,
        artifacts: tuple[ExportedArtifact, ...],
    ) -> None:
        if not artifacts:
            raise ExportPersistenceError("A exportação não produziu artefatos publicados.")
        with self._database.unit_of_work() as session:
            record = session.get(ExportRecord, export_id)
            if record is None or record.state != "running":
                raise ExportPersistenceError("A exportação não está ativa para conclusão.")
            record.artifacts.extend(
                ExportArtifactRecord(
                    id=uuid4(),
                    export_id=export_id,
                    package_id=artifact.package_id,
                    position=artifact.position,
                    format=artifact.format.value,
                    path=str(artifact.path),
                    sha256=artifact.sha256,
                    size_bytes=artifact.size_bytes,
                    chapter_ids=[str(chapter_id) for chapter_id in artifact.chapter_ids],
                    created_at=datetime.now(UTC),
                )
                for artifact in artifacts
            )
            record.state = "completed"
            record.error_code = None
            record.updated_at = datetime.now(UTC)

    def list_transfer_artifacts(self) -> tuple[ExportTransferArtifact, ...]:
        """Lista artefatos de exportações concluídas para envio manual explícito."""
        with self._database.unit_of_work() as session:
            records = session.execute(
                select(ExportArtifactRecord)
                .join(ExportRecord, ExportRecord.id == ExportArtifactRecord.export_id)
                .where(ExportRecord.state == "completed")
                .order_by(ExportArtifactRecord.created_at.desc(), ExportArtifactRecord.position)
            ).scalars()
            return tuple(_transfer_artifact(record) for record in records)

    def get_artifact(self, artifact_id: UUID) -> ExportTransferArtifact | None:
        with self._database.unit_of_work() as session:
            record = session.execute(
                select(ExportArtifactRecord)
                .join(ExportRecord, ExportRecord.id == ExportArtifactRecord.export_id)
                .where(
                    ExportArtifactRecord.id == artifact_id,
                    ExportRecord.state == "completed",
                )
            ).scalar_one_or_none()
            return _transfer_artifact(record) if record is not None else None


def _chapter_title(record: ChapterRecord) -> str:
    if record.title:
        return f"{record.title} ({record.number})" if record.number else record.title
    return f"Capítulo {record.number or ''}".strip()


def _optional_text(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        raise ExportSourceUnavailable("O número/volume salvo do capítulo é inválido.") from None
    if not decimal.is_finite():
        raise ExportSourceUnavailable("O número/volume salvo do capítulo é inválido.")
    return decimal


def _transfer_artifact(record: ExportArtifactRecord) -> ExportTransferArtifact:
    return ExportTransferArtifact(
        id=record.id,
        export_id=record.export_id,
        package_id=record.package_id,
        format=record.format,
        path=Path(record.path).expanduser().absolute(),
        sha256=record.sha256,
        size_bytes=record.size_bytes,
    )
