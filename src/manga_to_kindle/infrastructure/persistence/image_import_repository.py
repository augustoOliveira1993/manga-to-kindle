"""Publicação transacional de páginas importadas e derivados associados."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select

from manga_to_kindle.domain.image_processing import (
    ImageImportChapterTarget,
    ImageImportPlan,
    ImageImportResult,
    ImageImportTarget,
    ImageProcessingProfile,
    ImageTargetConflict,
    ImageTransformOptions,
    StagedImagePage,
)
from manga_to_kindle.domain.library import normalize_search_text
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    ChapterRecord,
    ImageImportJobRecord,
    MangaRecord,
    PageRecord,
    ProcessedPageRecord,
)


class ImageImportRepository:
    def __init__(self, database: SQLiteDatabase, image_root: Path) -> None:
        self._database = database
        self._image_root = image_root.expanduser().absolute()

    def list_targets(self) -> tuple[ImageImportChapterTarget, ...]:
        with self._database.unit_of_work() as session:
            rows = session.execute(
                select(ChapterRecord, MangaRecord)
                .join(MangaRecord, MangaRecord.id == ChapterRecord.manga_id)
                .where(
                    MangaRecord.simulated.is_(False),
                    ~select(PageRecord.id)
                    .where(
                        PageRecord.chapter_id == ChapterRecord.id,
                        PageRecord.import_job_id.is_(None),
                    )
                    .exists(),
                )
                .order_by(MangaRecord.title.collate("NOCASE"), ChapterRecord.position)
            ).all()
            return tuple(
                ImageImportChapterTarget(
                    manga_id=manga.id,
                    chapter_id=chapter.id,
                    manga_title=manga.title,
                    chapter_title=chapter.title or f"Capítulo {chapter.number or ''}".strip(),
                    chapter_number=chapter.number,
                    has_imported_pages=(
                        session.scalar(
                            select(func.count())
                            .select_from(PageRecord)
                            .where(PageRecord.chapter_id == chapter.id)
                        )
                        or 0
                    )
                    > 0,
                )
                for chapter, manga in rows
            )

    def start_job(
        self,
        job_id: UUID,
        plan: ImageImportPlan,
        target: ImageImportTarget,
    ) -> None:
        now = datetime.now(UTC)
        with self._database.unit_of_work() as session:
            manga = session.get(MangaRecord, target.manga_id)
            chapter = session.get(ChapterRecord, target.chapter_id)
            manga_title = target.manga_title if target.create_new else (
                manga.title if manga is not None else None
            )
            chapter_title = target.chapter_title if target.create_new else (
                chapter.title or f"Capítulo {chapter.number or ''}".strip()
                if chapter is not None
                else None
            )
            session.add(
                ImageImportJobRecord(
                    id=job_id,
                    source_kind=plan.source_kind.value,
                    source_fingerprint=plan.fingerprint,
                    target_manga_id=target.manga_id,
                    target_chapter_id=target.chapter_id,
                    manga_title_snapshot=manga_title,
                    chapter_title_snapshot=chapter_title,
                    state="staging",
                    total_images=len(plan.images),
                    completed_images=0,
                    created_at=now,
                    updated_at=now,
                )
            )

    def update_progress(self, job_id: UUID, completed: int) -> None:
        with self._database.unit_of_work() as session:
            job = session.get(ImageImportJobRecord, job_id)
            if job is None or job.state != "staging":
                return
            job.completed_images = min(max(0, completed), job.total_images)
            job.updated_at = datetime.now(UTC)

    def existing_hashes(self, hashes: tuple[str, ...]) -> frozenset[str]:
        if not hashes:
            return frozenset()
        with self._database.unit_of_work() as session:
            existing = session.scalars(
                select(PageRecord.source_sha256).where(PageRecord.source_sha256.in_(hashes))
            )
            return frozenset(value for value in existing if value is not None)

    def publish(
        self,
        job_id: UUID,
        plan: ImageImportPlan,
        target: ImageImportTarget,
        pages: tuple[StagedImagePage, ...],
        profile: ImageProcessingProfile,
        options: ImageTransformOptions,
    ) -> ImageImportResult:
        processed_count = sum(len(page.processed) for page in pages)
        duplicate_count = sum(page.duplicate_content for page in pages)
        with self._database.unit_of_work() as session:
            job = session.get(ImageImportJobRecord, job_id)
            if job is None or job.state != "staging":
                raise ImageTargetConflict("A importação não está pronta para publicação.")
            chapter = session.get(ChapterRecord, target.chapter_id)
            manga = session.get(MangaRecord, target.manga_id)
            if target.create_new:
                if chapter is not None or manga is not None:
                    raise ImageTargetConflict("O identificador do novo destino já está em uso.")
                manga = MangaRecord(
                    id=target.manga_id,
                    title=target.manga_title or "",
                    search_key=normalize_search_text(target.manga_title or ""),
                    provider_id="local-import",
                    source_ref=None,
                    simulated=False,
                )
                session.add(manga)
                session.flush()
                next_position = (
                    session.scalar(
                        select(func.max(ChapterRecord.position)).where(
                            ChapterRecord.manga_id == target.manga_id
                        )
                    )
                    or -1
                ) + 1
                chapter = ChapterRecord(
                    id=target.chapter_id,
                    manga_id=target.manga_id,
                    position=next_position,
                    title=target.chapter_title,
                    number=target.chapter_number,
                    search_key=normalize_search_text(
                        f"{target.chapter_title or ''} {target.chapter_number or ''}"
                    ),
                )
                session.add(chapter)
                session.flush()
            elif chapter is None or manga is None or chapter.manga_id != manga.id:
                raise ImageTargetConflict("O capítulo selecionado não existe mais.")
            if manga.simulated:
                raise ImageTargetConflict(
                    "Conteúdo de demonstração não pode receber imagens locais."
                )

            existing = tuple(
                session.scalars(
                    select(PageRecord)
                    .where(PageRecord.chapter_id == target.chapter_id)
                    .order_by(PageRecord.position)
                )
            )
            if existing:
                if _same_import(existing, pages):
                    job.state = "succeeded"
                    job.completed_images = len(plan.images)
                    job.updated_at = datetime.now(UTC)
                    return ImageImportResult(job_id, 0, 0, duplicate_count, idempotent=True)
                raise ImageTargetConflict(
                    "O capítulo já contém páginas diferentes; nenhuma página foi alterada."
                )

            _validate_managed_paths(job_id, pages, self._image_root)
            for page in pages:
                session.add(
                    PageRecord(
                        id=page.page_id,
                        chapter_id=target.chapter_id,
                        position=page.position,
                        original_path=str(page.final_original_path),
                        source_relative_path=page.relative_path.casefold(),
                        source_sha256=page.original_sha256,
                        source_media_type=page.media_type,
                        source_width=page.width,
                        source_height=page.height,
                        import_job_id=job_id,
                        duplicate_content=page.duplicate_content,
                    )
                )
                session.add_all(
                    ProcessedPageRecord(
                        id=uuid4(),
                        page_id=page.page_id,
                        output_order=processed.output_order,
                        path=str(processed.final_path),
                        sha256=processed.sha256,
                        width=processed.width,
                        height=processed.height,
                        profile_snapshot=_profile_snapshot(profile, options),
                        created_at=datetime.now(UTC),
                    )
                    for processed in page.processed
                )
            job.state = "succeeded"
            job.completed_images = len(plan.images)
            job.updated_at = datetime.now(UTC)
            session.flush()
        return ImageImportResult(job_id, len(pages), processed_count, duplicate_count)

    def fail_job(self, job_id: UUID, *, error_code: str, cancelled: bool = False) -> None:
        with self._database.unit_of_work() as session:
            job = session.get(ImageImportJobRecord, job_id)
            if job is None or job.state != "staging":
                return
            job.state = "cancelled" if cancelled else "failed"
            job.error_code = error_code
            job.updated_at = datetime.now(UTC)

    def staging_jobs(self) -> tuple[UUID, ...]:
        with self._database.unit_of_work() as session:
            return tuple(
                session.scalars(
                    select(ImageImportJobRecord.id).where(
                        ImageImportJobRecord.state == "staging"
                    )
                )
            )

    def mark_interrupted(self, job_id: UUID) -> None:
        with self._database.unit_of_work() as session:
            job = session.get(ImageImportJobRecord, job_id)
            if job is None or job.state != "staging":
                return
            job.state = "interrupted"
            job.error_code = "IMPORT_INTERRUPTED"
            job.updated_at = datetime.now(UTC)

    def get_pages(self, chapter_id: UUID) -> tuple[PageRecord, ...]:
        with self._database.unit_of_work() as session:
            return tuple(
                session.scalars(
                    select(PageRecord)
                    .where(PageRecord.chapter_id == chapter_id)
                    .order_by(PageRecord.position)
                )
            )

    def get_processed_pages(self, page_id: UUID) -> tuple[ProcessedPageRecord, ...]:
        with self._database.unit_of_work() as session:
            return tuple(
                session.scalars(
                    select(ProcessedPageRecord)
                    .where(ProcessedPageRecord.page_id == page_id)
                    .order_by(ProcessedPageRecord.output_order)
                )
            )

    def get_job(self, job_id: UUID) -> ImageImportJobRecord | None:
        with self._database.unit_of_work() as session:
            return session.get(ImageImportJobRecord, job_id)


def _same_import(existing: tuple[PageRecord, ...], incoming: tuple[StagedImagePage, ...]) -> bool:
    if len(existing) != len(incoming):
        return False
    return all(
        current.position == candidate.position
        and (current.source_relative_path or "").casefold() == candidate.relative_path.casefold()
        and current.source_sha256 == candidate.original_sha256
        for current, candidate in zip(existing, incoming, strict=True)
    )


def _validate_managed_paths(
    job_id: UUID,
    pages: tuple[StagedImagePage, ...],
    image_root: Path,
) -> None:
    expected_root = image_root / "imports" / str(job_id)
    try:
        resolved_root = expected_root.resolve(strict=True)
        if expected_root.is_symlink() or not resolved_root.is_relative_to(image_root.resolve()):
            raise ImageTargetConflict("A pasta final não pertence ao armazenamento gerenciado.")
    except OSError:
        raise ImageTargetConflict("A pasta final da importação não foi encontrada.") from None
    for page in pages:
        for candidate in (page.final_original_path, *(item.final_path for item in page.processed)):
            try:
                resolved = candidate.resolve(strict=True)
                if (
                    candidate.is_symlink()
                    or not resolved.is_relative_to(resolved_root)
                    or not resolved.is_file()
                ):
                    raise ImageTargetConflict(
                        "Uma imagem final não pertence à pasta gerenciada da importação."
                    )
            except OSError:
                raise ImageTargetConflict(
                    "Uma imagem final da importação não foi encontrada."
                ) from None


def _profile_snapshot(
    profile: ImageProcessingProfile,
    options: ImageTransformOptions,
) -> dict[str, object]:
    return {
        "name": profile.name,
        "width": profile.width,
        "height": profile.height,
        "margin_left": profile.margin_left,
        "margin_top": profile.margin_top,
        "margin_right": profile.margin_right,
        "margin_bottom": profile.margin_bottom,
        "crop_margins": options.crop_margins,
        "split_double_pages": options.split_double_pages,
        "reading_direction": options.reading_direction.value,
    }
