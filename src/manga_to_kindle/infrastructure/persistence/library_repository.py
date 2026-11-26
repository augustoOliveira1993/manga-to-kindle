"""Consultas, favoritos e histórico derivados dos registros F003–F007."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from manga_to_kindle.application.library.availability import (
    AvailabilityEvidence,
    classify_availability,
)
from manga_to_kindle.domain.library import (
    ActivityKind,
    AvailabilityState,
    LibraryActivity,
    LibraryAsset,
    LibraryAssetCategory,
    LibraryAssetState,
    LibraryDeletionPreview,
    LibraryDeletionResult,
    LibraryEntry,
    LibraryPage,
    LibraryPreferences,
    LibraryQuery,
    LibrarySort,
)
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    CatalogMembershipRecord,
    ChapterRecord,
    DownloadChapterRecord,
    DownloadJobRecord,
    DownloadPageRecord,
    ExportArtifactRecord,
    ExportChapterRecord,
    ExportRecord,
    ImageImportJobRecord,
    LibraryAssetRecord,
    LibraryDeletionItemRecord,
    LibraryDeletionPlanRecord,
    LibraryPreferenceRecord,
    MangaRecord,
    PageRecord,
    ProcessedPageRecord,
)


class LibraryPersistenceError(RuntimeError):
    code = "LIBRARY_PERSISTENCE_FAILED"


class LibraryRepository:
    """Abre sessões por operação e não retorna objetos ORM ao chamador."""

    def __init__(self, database: SQLiteDatabase, managed_roots: tuple[Path, ...] = ()) -> None:
        self._database = database
        self._managed_roots = tuple(path.resolve() for path in managed_roots)

    def search(self, query: LibraryQuery) -> LibraryPage:
        with self._database.unit_of_work() as session:
            statement = select(MangaRecord, ChapterRecord).outerjoin(
                ChapterRecord, ChapterRecord.manga_id == MangaRecord.id
            )
            if query.favorite_only:
                statement = statement.where(
                    or_(MangaRecord.favorite.is_(True), ChapterRecord.favorite.is_(True))
                )
            if query.normalized_search:
                term = query.normalized_search
                statement = statement.where(
                    or_(
                        func.instr(MangaRecord.search_key, term) > 0,
                        func.instr(ChapterRecord.search_key, term) > 0,
                    )
                )
            total_statement = select(func.count()).select_from(statement.order_by(None).subquery())
            total = int(session.scalar(total_statement) or 0)
            statement = self._apply_sort(statement, query.sort)
            materialize = (
                query.availability is not None
                or query.download_state is not None
                or query.export_state is not None
                or query.sort in {LibrarySort.ACTIVITY, LibrarySort.STATE}
            )
            if not materialize:
                rows = [
                    (manga, chapter)
                    for manga, chapter in session.execute(
                        statement.offset(query.offset).limit(query.limit)
                    )
                ]
            else:
                rows = [(manga, chapter) for manga, chapter in session.execute(statement)]

            entries = self._map_rows(session, rows)
            if query.availability is not None:
                entries = [item for item in entries if item.availability is query.availability]
            if query.download_state is not None:
                entries = [item for item in entries if item.download_state == query.download_state]
            if query.export_state is not None:
                entries = [item for item in entries if item.export_state == query.export_state]
            if materialize:
                total = len(entries)
                if query.sort is LibrarySort.ACTIVITY:
                    entries.sort(
                        key=lambda item: (item.updated_at, str(item.manga_id)),
                        reverse=True,
                    )
                elif query.sort is LibrarySort.STATE:
                    order = {state: index for index, state in enumerate(AvailabilityState)}
                    entries.sort(
                        key=lambda item: (
                            order[item.availability],
                            item.manga_title.casefold(),
                            item.chapter_position if item.chapter_position is not None else -1,
                            str(item.chapter_id or item.manga_id),
                        )
                    )
                entries = entries[query.offset : query.offset + query.limit]
            return LibraryPage(entries=tuple(entries), total=total)

    def history(self, *, limit: int = 100) -> tuple[LibraryActivity, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("O histórico deve carregar de 1 a 500 registros por vez.")
        with self._database.unit_of_work() as session:
            activities: list[LibraryActivity] = []
            download_rows = session.execute(
                select(DownloadJobRecord, MangaRecord, ChapterRecord)
                .outerjoin(ChapterRecord, ChapterRecord.id == DownloadJobRecord.chapter_id)
                .outerjoin(
                    MangaRecord,
                    or_(
                        MangaRecord.id == DownloadJobRecord.manga_id,
                        MangaRecord.id == ChapterRecord.manga_id,
                    ),
                )
                .order_by(DownloadJobRecord.updated_at.desc(), DownloadJobRecord.id)
                .limit(limit)
            ).all()
            for download_job, manga, chapter in download_rows:
                identity = _identity(manga.title if manga is not None else None, chapter)
                activities.append(
                    LibraryActivity(
                        id=download_job.id,
                        kind=ActivityKind.DOWNLOAD,
                        identity=identity,
                        state=download_job.state,
                        started_at=_as_utc(download_job.created_at),
                        ended_at=_as_utc(download_job.updated_at),
                        reason_code=download_job.error_code,
                    )
                )

            import_rows = session.execute(
                select(ImageImportJobRecord, MangaRecord, ChapterRecord)
                .outerjoin(MangaRecord, MangaRecord.id == ImageImportJobRecord.target_manga_id)
                .outerjoin(
                    ChapterRecord,
                    ChapterRecord.id == ImageImportJobRecord.target_chapter_id,
                )
                .order_by(ImageImportJobRecord.updated_at.desc(), ImageImportJobRecord.id)
                .limit(limit)
            ).all()
            for import_job, manga, chapter in import_rows:
                activities.append(
                    LibraryActivity(
                        id=import_job.id,
                        kind=ActivityKind.IMAGE_IMPORT,
                        identity=_import_identity(import_job, manga, chapter),
                        state=import_job.state,
                        started_at=_as_utc(import_job.created_at),
                        ended_at=_as_utc(import_job.updated_at),
                        reason_code=import_job.error_code,
                    )
                )

            export_rows = tuple(
                session.scalars(
                    select(ExportRecord)
                    .order_by(ExportRecord.updated_at.desc(), ExportRecord.id)
                    .limit(limit)
                )
            )
            for export in export_rows:
                artifacts = tuple(
                    session.scalars(
                        select(ExportArtifactRecord)
                        .where(ExportArtifactRecord.export_id == export.id)
                        .order_by(ExportArtifactRecord.position)
                    )
                )
                artifact_formats = tuple(item.format for item in artifacts)
                linked_chapters = int(
                    session.scalar(
                        select(func.count())
                        .select_from(ExportChapterRecord)
                        .where(ExportChapterRecord.export_id == export.id)
                    )
                    or 0
                )
                artifact_chapters = {
                    chapter_id for artifact in artifacts for chapter_id in artifact.chapter_ids
                }
                chapter_count = max(
                    linked_chapters,
                    len(artifact_chapters),
                    _snapshot_chapter_count(export.profile_snapshot),
                )
                format_names = ", ".join(dict.fromkeys(item.upper() for item in artifact_formats))
                identity = _export_identity(export.profile_snapshot, chapter_count)
                if format_names:
                    identity = f"{identity} · {format_names}"
                activities.append(
                    LibraryActivity(
                        id=export.id,
                        kind=ActivityKind.EXPORT,
                        identity=identity,
                        state=export.state,
                        started_at=_as_utc(export.created_at),
                        ended_at=_as_utc(export.updated_at),
                        reason_code=export.error_code,
                        location_name=Path(export.destination).name or None,
                    )
                )

            activities.sort(
                key=lambda activity: (activity.ended_at, str(activity.id)),
                reverse=True,
            )
            return tuple(activities[:limit])

    def set_favorite(self, *, manga_id: UUID, chapter_id: UUID | None, favorite: bool) -> None:
        with self._database.unit_of_work() as session:
            if chapter_id is None:
                manga = session.get(MangaRecord, manga_id)
                if manga is None:
                    raise LibraryPersistenceError("O mangá não está mais na biblioteca.")
                manga.favorite = favorite
                return
            chapter = session.get(ChapterRecord, chapter_id)
            if chapter is None or chapter.manga_id != manga_id:
                raise LibraryPersistenceError("O capítulo não pertence ao mangá selecionado.")
            chapter.favorite = favorite

    def get_preferences(self) -> LibraryPreferences:
        with self._database.unit_of_work() as session:
            preference = session.get(LibraryPreferenceRecord, 1)
            if preference is None:
                return LibraryPreferences()
            availability = (
                AvailabilityState(preference.availability_filter)
                if preference.availability_filter is not None
                else None
            )
            return LibraryPreferences(
                favorite_only=preference.favorite_only,
                availability=availability,
                download_state=preference.download_state,
                export_state=preference.export_state,
                sort=LibrarySort(preference.sort_order),
            )

    def save_preferences(self, preferences: LibraryPreferences) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(LibraryPreferenceRecord, 1)
            if record is None:
                record = LibraryPreferenceRecord(id=1)
                session.add(record)
            record.favorite_only = preferences.favorite_only
            record.availability_filter = (
                preferences.availability.value if preferences.availability is not None else None
            )
            record.download_state = preferences.download_state
            record.export_state = preferences.export_state
            record.sort_order = preferences.sort.value
            record.updated_at = datetime.now(UTC)

    def preview_delete(self, manga_id: UUID) -> LibraryDeletionPreview:
        with self._database.unit_of_work() as session:
            manga = session.get(MangaRecord, manga_id)
            if manga is None:
                raise LibraryPersistenceError("O mangá não está mais na biblioteca.")
            chapters = tuple(
                session.scalars(
                    select(ChapterRecord)
                    .where(ChapterRecord.manga_id == manga_id)
                    .order_by(ChapterRecord.position, ChapterRecord.id)
                )
            )
            chapter_ids = tuple(chapter.id for chapter in chapters)
            pages = (
                tuple(
                    session.scalars(
                        select(PageRecord).where(PageRecord.chapter_id.in_(chapter_ids))
                    )
                )
                if chapter_ids
                else ()
            )
            page_ids = tuple(page.id for page in pages)
            processed = (
                tuple(
                    session.scalars(
                        select(ProcessedPageRecord).where(
                            ProcessedPageRecord.page_id.in_(page_ids)
                        )
                    )
                )
                if page_ids
                else ()
            )
            download_job_conditions = [DownloadJobRecord.manga_id == manga_id]
            if chapter_ids:
                download_job_conditions.append(
                    DownloadJobRecord.chapter_id.in_(chapter_ids)
                )
            download_jobs = tuple(
                session.scalars(
                    select(DownloadJobRecord).where(or_(*download_job_conditions))
                )
            )
            download_job_ids = tuple(job.id for job in download_jobs)
            download_page_conditions = []
            if chapter_ids:
                download_page_conditions.append(
                    DownloadPageRecord.chapter_id.in_(chapter_ids)
                )
            if download_job_ids:
                download_page_conditions.append(
                    DownloadPageRecord.job_id.in_(download_job_ids)
                )
            download_pages = tuple(
                session.scalars(
                    select(DownloadPageRecord).where(or_(*download_page_conditions))
                )
            ) if download_page_conditions else ()
            download_chapters = (
                tuple(
                    session.scalars(
                        select(DownloadChapterRecord).where(
                            DownloadChapterRecord.chapter_id.in_(chapter_ids)
                        )
                    )
                )
                if chapter_ids
                else ()
            )
            import_jobs = tuple(
                session.scalars(
                    select(ImageImportJobRecord).where(
                        ImageImportJobRecord.target_manga_id == manga_id
                    )
                )
            )
            export_links = (
                tuple(
                    session.scalars(
                        select(ExportChapterRecord).where(
                            ExportChapterRecord.chapter_id.in_(chapter_ids)
                        )
                    )
                )
                if chapter_ids
                else ()
            )
            export_ids = tuple(dict.fromkeys(link.export_id for link in export_links))
            export_artifacts = (
                tuple(
                    session.scalars(
                        select(ExportArtifactRecord).where(
                            ExportArtifactRecord.export_id.in_(export_ids)
                        )
                    )
                )
                if export_ids
                else ()
            )

            hash_by_path = {
                _path_key(Path(item.original_path)): item.sha256
                for item in download_pages
                if item.original_path is not None and item.sha256 is not None
            }
            assets_by_path: dict[str, LibraryAsset] = {}
            for page in pages:
                path = Path(page.original_path)
                self._add_preview_asset(
                    assets_by_path,
                    asset_id=f"page:{page.id}",
                    category=LibraryAssetCategory.ORIGINAL,
                    path=path,
                    sha256=page.source_sha256 or hash_by_path.get(_path_key(path)),
                    media_type=page.source_media_type,
                )
            for processed_item in processed:
                self._add_preview_asset(
                    assets_by_path,
                    asset_id=f"processed:{processed_item.id}",
                    category=LibraryAssetCategory.PROCESSED,
                    path=Path(processed_item.path),
                    sha256=processed_item.sha256,
                    media_type="image/png",
                )
            for item in download_pages:
                if item.original_path is None:
                    continue
                self._add_preview_asset(
                    assets_by_path,
                    asset_id=f"download:{item.id}",
                    category=LibraryAssetCategory.DOWNLOAD,
                    path=Path(item.original_path),
                    sha256=item.sha256,
                    media_type=None,
                    known_size=item.byte_size,
                )
            selected_chapter_ids = {str(item) for item in chapter_ids}
            for artifact in export_artifacts:
                if not set(artifact.chapter_ids).issubset(selected_chapter_ids):
                    continue
                self._add_preview_asset(
                    assets_by_path,
                    asset_id=f"export:{artifact.id}",
                    category=LibraryAssetCategory.EXPORT,
                    path=Path(artifact.path),
                    sha256=artifact.sha256,
                    media_type=artifact.format,
                    known_size=artifact.size_bytes,
                )

            assets_by_path = {
                key: replace(
                    asset,
                    shared=self._path_is_shared(
                        session,
                        asset.path,
                        selected_chapter_ids=chapter_ids,
                        selected_manga_id=manga_id,
                    ),
                )
                for key, asset in assets_by_path.items()
            }

            membership_ids = tuple(
                session.scalars(
                    select(CatalogMembershipRecord.chapter_id).where(
                        CatalogMembershipRecord.manga_id == manga_id
                    )
                )
            )
            record_ids: list[tuple[str, str]] = [("manga", str(manga_id))]
            record_ids.extend(("chapter", str(item.id)) for item in chapters)
            record_ids.extend(("catalog_membership", str(item)) for item in membership_ids)
            record_ids.extend(("page", str(item.id)) for item in pages)
            record_ids.extend(("processed_page", str(item.id)) for item in processed)
            record_ids.extend(("download_job", str(item.id)) for item in download_jobs)
            record_ids.extend(("download_page", str(item.id)) for item in download_pages)
            record_ids.extend(
                ("download_chapter", f"{item.job_id}:{item.chapter_id}")
                for item in download_chapters
            )
            record_ids.extend(
                ("export_chapter", f"{item.export_id}:{item.chapter_id}")
                for item in export_links
            )
            counts = (
                ("mangá", 1),
                ("capítulos", len(chapters)),
                ("vínculos de catálogo", len(membership_ids)),
                ("páginas originais", len(pages)),
                ("páginas processadas", len(processed)),
                ("trabalhos de download", len(download_jobs)),
                ("páginas de download", len(download_pages)),
                ("progresso de download", len(download_chapters)),
                ("vínculos de exportação", len(export_links)),
                ("histórico de exportação preservado", len(export_ids)),
                ("artefatos de exportação preservados", len(export_artifacts)),
                ("arquivos", len(assets_by_path)),
                ("histórico de importação preservado", len(import_jobs)),
            )
            return LibraryDeletionPreview(
                manga_id=manga_id,
                manga_title=manga.title,
                chapter_ids=chapter_ids,
                record_ids=tuple(record_ids),
                record_counts=counts,
                assets=tuple(
                    sorted(
                        assets_by_path.values(),
                        key=lambda item: (item.category.value, item.path.name.casefold()),
                    )
                ),
            )

    def delete_scope(
        self,
        preview: LibraryDeletionPreview,
        *,
        asset_ids: tuple[str, ...],
        confirmed: bool,
    ) -> LibraryDeletionResult:
        if not confirmed:
            raise LibraryPersistenceError("A exclusão requer confirmação explícita.")
        if len(asset_ids) != len(set(asset_ids)):
            raise LibraryPersistenceError("A seleção de arquivos contém IDs repetidos.")
        current = self.preview_delete(preview.manga_id)
        if current != preview:
            raise LibraryPersistenceError(
                "A biblioteca mudou desde a prévia; atualize o resumo antes de confirmar."
            )
        assets_by_id = {item.id: item for item in current.assets}
        if not set(asset_ids).issubset(assets_by_id):
            raise LibraryPersistenceError("A seleção contém arquivo que não aparece na prévia.")
        selected_assets = tuple(assets_by_id[item] for item in asset_ids)
        if any(
            not asset.managed and asset.category is not LibraryAssetCategory.EXPORT
            for asset in selected_assets
        ):
            raise LibraryPersistenceError(
                "Somente cópias gerenciadas ou exports registrados podem ser excluídos."
            )
        if any(asset.shared for asset in selected_assets):
            raise LibraryPersistenceError(
                "Um arquivo compartilhado por outro registro será preservado."
            )
        if any(
            asset.state is LibraryAssetState.AVAILABLE and asset.sha256 is None
            for asset in selected_assets
        ):
            raise LibraryPersistenceError(
                "O arquivo não tem checksum registrado para conferência."
            )
        return self._execute_deletion(
            current,
            selected_assets=selected_assets,
            delete_records=True,
        )

    def list_unlinked_assets(self) -> tuple[LibraryAsset, ...]:
        with self._database.unit_of_work() as session:
            records = tuple(
                session.scalars(
                    select(LibraryAssetRecord).order_by(
                        LibraryAssetRecord.created_at.desc(), LibraryAssetRecord.id
                    )
                )
            )
            return tuple(
                replace(
                    _orphan_asset(record, self._managed_roots),
                    shared=self._path_is_shared(
                        session,
                        Path(record.path),
                        selected_chapter_ids=(),
                        selected_manga_id=UUID(int=0),
                    ),
                )
                for record in records
            )

    def delete_unlinked_assets(
        self,
        asset_ids: tuple[str, ...],
        *,
        confirmed: bool,
    ) -> LibraryDeletionResult:
        if not confirmed:
            raise LibraryPersistenceError("A exclusão requer confirmação explícita.")
        if len(asset_ids) != len(set(asset_ids)):
            raise LibraryPersistenceError("A seleção de arquivos contém IDs repetidos.")
        assets = {item.id: item for item in self.list_unlinked_assets()}
        if not set(asset_ids).issubset(assets):
            raise LibraryPersistenceError("A seleção contém arquivo sem vínculo que não existe.")
        if any(assets[item].shared for item in asset_ids):
            raise LibraryPersistenceError("Um arquivo usado por outro registro será preservado.")
        if any(
            assets[item].state is LibraryAssetState.UNLINKED
            and assets[item].sha256 is None
            for item in asset_ids
        ):
            raise LibraryPersistenceError(
                "O arquivo não tem checksum registrado para conferência."
            )
        return self._execute_deletion(
            None,
            selected_assets=tuple(assets[item] for item in asset_ids),
            delete_records=False,
        )

    def recover_deletions(self) -> int:
        with self._database.unit_of_work() as session:
            plans = tuple(
                session.scalars(
                    select(LibraryDeletionPlanRecord).where(
                        LibraryDeletionPlanRecord.state.in_(("planned", "running"))
                    )
                )
            )
            for plan in plans:
                plan.state = "partial"
                plan.error_code = "DELETE_INTERRUPTED"
                plan.updated_at = datetime.now(UTC)
                items = tuple(
                    session.scalars(
                        select(LibraryDeletionItemRecord).where(
                            LibraryDeletionItemRecord.plan_id == plan.id,
                            LibraryDeletionItemRecord.state == "pending",
                        )
                    )
                )
                for item in items:
                    if item.kind == "asset" and item.path is not None:
                        _actual, _size, file_state = _inspect_file(
                            Path(item.path), item.sha256
                        )
                        item.state = {
                            "available": "failed",
                            "missing": "missing",
                            "altered": "changed",
                        }[file_state]
                    else:
                        item.state = "failed"
                    item.error_code = "DELETE_INTERRUPTED"
            return len(plans)

    def _add_preview_asset(
        self,
        assets: dict[str, LibraryAsset],
        *,
        asset_id: str,
        category: LibraryAssetCategory,
        path: Path,
        sha256: str | None,
        media_type: str | None,
        known_size: int | None = None,
    ) -> None:
        key = _path_key(path)
        actual_hash, actual_size, file_state = _inspect_file(path, sha256)
        expected_hash = sha256 or actual_hash
        state = {
            "available": LibraryAssetState.AVAILABLE,
            "missing": LibraryAssetState.MISSING,
            "altered": LibraryAssetState.CHANGED,
        }[file_state]
        if key in assets:
            existing = assets[key]
            if existing.sha256 != expected_hash:
                state = LibraryAssetState.CHANGED
            # The first relationship defines the category. One physical path is
            # presented and selectable only once even when Page and DownloadPage
            # share its identity.
            assets[key] = LibraryAsset(
                id=existing.id,
                category=existing.category,
                path=existing.path,
                sha256=existing.sha256,
                size_bytes=existing.size_bytes,
                media_type=existing.media_type,
                managed=existing.managed,
                state=state if state is not LibraryAssetState.AVAILABLE else existing.state,
            )
            return
        assets[key] = LibraryAsset(
            id=f"asset:{hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]}",
            category=category,
            path=path,
            sha256=expected_hash,
            size_bytes=known_size if known_size is not None else actual_size,
            media_type=media_type,
            managed=_is_managed_path(path, self._managed_roots),
            state=state,
        )

    @staticmethod
    def _path_is_shared(
        session: Session,
        path: Path,
        *,
        selected_chapter_ids: tuple[UUID, ...],
        selected_manga_id: UUID,
    ) -> bool:
        value = str(path)
        page_statement = select(PageRecord.id).where(PageRecord.original_path == value)
        if selected_chapter_ids:
            page_statement = page_statement.where(
                PageRecord.chapter_id.not_in(selected_chapter_ids)
            )
        if session.scalar(page_statement.limit(1)) is not None:
            return True
        processed_statement = (
            select(ProcessedPageRecord.id)
            .join(PageRecord, PageRecord.id == ProcessedPageRecord.page_id)
            .where(ProcessedPageRecord.path == value)
        )
        if selected_chapter_ids:
            processed_statement = processed_statement.where(
                PageRecord.chapter_id.not_in(selected_chapter_ids)
            )
        if session.scalar(processed_statement.limit(1)) is not None:
            return True
        download_statement = select(DownloadPageRecord.id).where(
            DownloadPageRecord.original_path == value
        )
        if selected_chapter_ids:
            download_statement = download_statement.where(
                DownloadPageRecord.chapter_id.not_in(selected_chapter_ids)
            )
        if session.scalar(download_statement.limit(1)) is not None:
            return True
        if session.scalar(
            select(MangaRecord.id)
            .where(MangaRecord.cover_path == value)
            .where(MangaRecord.id != selected_manga_id)
            .limit(1)
        ) is not None:
            return True
        for artifact in session.scalars(
            select(ExportArtifactRecord).where(ExportArtifactRecord.path == value)
        ):
            if not set(artifact.chapter_ids).issubset(
                {str(item) for item in selected_chapter_ids}
            ):
                return True
        return False

    def _execute_deletion(
        self,
        preview: LibraryDeletionPreview | None,
        *,
        selected_assets: tuple[LibraryAsset, ...],
        delete_records: bool,
    ) -> LibraryDeletionResult:
        plan_id = uuid4()
        now = datetime.now(UTC)
        record_ids = preview.record_ids if preview is not None else ()
        all_assets = preview.assets if preview is not None else selected_assets
        summary = {
            "manga_id": str(preview.manga_id) if preview is not None else None,
            "record_ids": [list(item) for item in record_ids],
            "delete_records": delete_records,
            "assets": [
                {
                    "id": item.id,
                    "category": item.category.value,
                    "path": str(item.path),
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                }
                for item in all_assets
            ],
        }
        with self._database.unit_of_work() as session:
            plan = LibraryDeletionPlanRecord(
                id=plan_id,
                state="planned",
                summary=summary,
                created_at=now,
                updated_at=now,
            )
            session.add(plan)
            session.flush()
            for kind, target in record_ids:
                session.add(
                    LibraryDeletionItemRecord(
                        id=uuid4(),
                        plan_id=plan_id,
                        kind="record",
                        target_id=hashlib.sha256(f"{kind}:{target}".encode()).hexdigest(),
                        state="pending",
                    )
                )
            for asset in selected_assets:
                session.add(
                    LibraryDeletionItemRecord(
                        id=uuid4(),
                        plan_id=plan_id,
                        kind="asset",
                        target_id=asset.id,
                        category=asset.category.value,
                        path=str(asset.path),
                        sha256=asset.sha256,
                        size_bytes=asset.size_bytes,
                        state="pending",
                    )
                )

        selected_ids = {asset.id for asset in selected_assets}
        asset_outcomes: dict[str, str] = {}
        for asset in selected_assets:
            outcome = "preserved"
            if asset.shared:
                outcome = "preserved"
            elif asset.state is LibraryAssetState.MISSING:
                outcome = "missing"
            elif asset.state is LibraryAssetState.CHANGED:
                outcome = "changed"
            elif not asset.managed and asset.category is not LibraryAssetCategory.EXPORT:
                outcome = "preserved"
            else:
                actual_hash, _size, state = _inspect_file(asset.path)
                if state == "missing":
                    outcome = "missing"
                elif state == "altered" or actual_hash != asset.sha256:
                    outcome = "changed"
                elif asset.path.is_symlink():
                    outcome = "changed"
                else:
                    try:
                        asset.path.unlink()
                    except OSError:
                        outcome = "failed"
                    else:
                        outcome = "deleted"
            asset_outcomes[asset.id] = outcome

        with self._database.unit_of_work() as session:
            deletion_plan = session.get(LibraryDeletionPlanRecord, plan_id)
            if deletion_plan is None:
                raise LibraryPersistenceError("O plano de exclusão não foi persistido.")
            deletion_plan.state = "running"
            deletion_plan.updated_at = datetime.now(UTC)
            plan_items = tuple(
                session.scalars(
                    select(LibraryDeletionItemRecord).where(
                        LibraryDeletionItemRecord.plan_id == plan_id
                    )
                )
            )
            for item in plan_items:
                if item.kind == "asset":
                    item.state = asset_outcomes[item.target_id]
                else:
                    item.state = "deleted" if delete_records else "preserved"

            for asset in all_assets:
                stored_outcome = asset_outcomes.get(asset.id)
                if asset.category is LibraryAssetCategory.EXPORT or asset.shared:
                    continue
                existing = session.scalar(
                    select(LibraryAssetRecord).where(LibraryAssetRecord.path == str(asset.path))
                )
                if asset.id in selected_ids and stored_outcome == "deleted":
                    if existing is not None:
                        session.delete(existing)
                    continue
                state = (
                    stored_outcome
                    if stored_outcome in {"missing", "changed"}
                    else "unlinked"
                )
                if state == "failed" or stored_outcome == "failed":
                    state = "unlinked"
                if existing is None:
                    session.add(
                        LibraryAssetRecord(
                            id=uuid4(),
                            category=asset.category.value,
                            path=str(asset.path),
                            sha256=asset.sha256,
                            size_bytes=asset.size_bytes,
                            media_type=asset.media_type,
                            managed=asset.managed,
                            state=state,
                            created_at=datetime.now(UTC),
                        )
                    )
                else:
                    existing.state = state

            if delete_records and preview is not None:
                chapter_ids = preview.chapter_ids
                page_ids = tuple(
                    session.scalars(
                        select(PageRecord.id).where(PageRecord.chapter_id.in_(chapter_ids))
                    )
                ) if chapter_ids else ()
                job_conditions = [DownloadJobRecord.manga_id == preview.manga_id]
                if chapter_ids:
                    job_conditions.append(
                        DownloadJobRecord.chapter_id.in_(chapter_ids)
                    )
                job_ids = tuple(
                    session.scalars(
                        select(DownloadJobRecord.id).where(or_(*job_conditions))
                    )
                )
                if page_ids:
                    session.execute(
                        delete(ProcessedPageRecord).where(
                            ProcessedPageRecord.page_id.in_(page_ids)
                        )
                    )
                    session.execute(delete(PageRecord).where(PageRecord.id.in_(page_ids)))
                if chapter_ids or job_ids:
                    conditions = []
                    if chapter_ids:
                        conditions.append(DownloadPageRecord.chapter_id.in_(chapter_ids))
                    if job_ids:
                        conditions.append(DownloadPageRecord.job_id.in_(job_ids))
                    session.execute(delete(DownloadPageRecord).where(or_(*conditions)))
                if chapter_ids:
                    session.execute(
                        delete(DownloadChapterRecord).where(
                            DownloadChapterRecord.chapter_id.in_(chapter_ids)
                        )
                    )
                    session.execute(
                        delete(ExportChapterRecord).where(
                            ExportChapterRecord.chapter_id.in_(chapter_ids)
                        )
                    )
                    session.execute(
                        delete(CatalogMembershipRecord).where(
                            CatalogMembershipRecord.manga_id == preview.manga_id
                        )
                    )
                if job_ids:
                    session.execute(delete(DownloadJobRecord).where(DownloadJobRecord.id.in_(job_ids)))
                if chapter_ids:
                    session.execute(delete(ChapterRecord).where(ChapterRecord.id.in_(chapter_ids)))
                session.execute(delete(MangaRecord).where(MangaRecord.id == preview.manga_id))

            failed_or_changed = any(
                outcome in {"failed", "changed", "preserved"}
                for outcome in asset_outcomes.values()
            )
            plan.state = "partial" if failed_or_changed else "completed"
            plan.error_code = (
                "ASSET_DELETE_INCOMPLETE" if failed_or_changed else None
            )
            plan.updated_at = datetime.now(UTC)

        deleted_files = sum(outcome == "deleted" for outcome in asset_outcomes.values())
        preserved_files = len(asset_outcomes) - deleted_files
        return LibraryDeletionResult(
            plan_id=plan_id,
            state="partial" if failed_or_changed else "completed",
            removed_record_count=len(record_ids) if delete_records else 0,
            removed_file_count=deleted_files,
            preserved_file_count=preserved_files,
            error_code="ASSET_DELETE_INCOMPLETE" if failed_or_changed else None,
        )

    @staticmethod
    def _apply_sort(
        statement: Select[MangaRecord, ChapterRecord],
        sort: LibrarySort,
    ) -> Select[MangaRecord, ChapterRecord]:
        if sort is LibrarySort.ACTIVITY:
            return statement.order_by(
                MangaRecord.updated_at.desc(),
                ChapterRecord.position.desc().nullslast(),
                MangaRecord.id,
                ChapterRecord.id,
            )
        if sort is LibrarySort.CHAPTER:
            return statement.order_by(
                MangaRecord.title.collate("NOCASE"),
                ChapterRecord.position,
                MangaRecord.id,
                ChapterRecord.id,
            )
        if sort is LibrarySort.STATE:
            return statement.order_by(
                ChapterRecord.available.desc().nullslast(),
                MangaRecord.title.collate("NOCASE"),
                ChapterRecord.position,
                MangaRecord.id,
                ChapterRecord.id,
            )
        return statement.order_by(
            MangaRecord.title.collate("NOCASE"),
            ChapterRecord.position.nulls_first(),
            MangaRecord.id,
            ChapterRecord.id,
        )

    def _map_rows(
        self,
        session: Session,
        rows: Sequence[tuple[MangaRecord, ChapterRecord | None]],
    ) -> list[LibraryEntry]:
        chapter_ids = tuple(
            chapter.id for _manga, chapter in rows if chapter is not None
        )
        pages_by_chapter: dict[UUID, list[PageRecord]] = {
            chapter_id: [] for chapter_id in chapter_ids
        }
        if chapter_ids:
            for page in session.scalars(
                select(PageRecord)
                .where(PageRecord.chapter_id.in_(chapter_ids))
                .order_by(PageRecord.chapter_id, PageRecord.position)
            ):
                pages_by_chapter.setdefault(page.chapter_id, []).append(page)

        page_ids = tuple(page.id for pages in pages_by_chapter.values() for page in pages)
        processed_by_page: dict[UUID, list[ProcessedPageRecord]] = {
            page_id: [] for page_id in page_ids
        }
        if page_ids:
            for processed in session.scalars(
                select(ProcessedPageRecord)
                .where(ProcessedPageRecord.page_id.in_(page_ids))
                .order_by(ProcessedPageRecord.page_id, ProcessedPageRecord.output_order)
            ):
                processed_by_page.setdefault(processed.page_id, []).append(processed)

        download_evidence: dict[UUID, list[tuple[DownloadChapterRecord, DownloadJobRecord]]] = {}
        if chapter_ids:
            for chapter_download, job in session.execute(
                select(DownloadChapterRecord, DownloadJobRecord)
                .join(DownloadJobRecord, DownloadJobRecord.id == DownloadChapterRecord.job_id)
                .where(DownloadChapterRecord.chapter_id.in_(chapter_ids))
                .order_by(DownloadJobRecord.updated_at.desc())
            ):
                download_evidence.setdefault(chapter_download.chapter_id, []).append(
                    (chapter_download, job)
                )

        download_pages: dict[tuple[UUID, UUID], list[DownloadPageRecord]] = {}
        if chapter_ids:
            for download_page in session.scalars(
                select(DownloadPageRecord)
                .where(DownloadPageRecord.chapter_id.in_(chapter_ids))
                .order_by(DownloadPageRecord.position)
            ):
                download_pages.setdefault(
                    (download_page.job_id, download_page.chapter_id), []
                ).append(download_page)

        import_evidence: dict[UUID, list[ImageImportJobRecord]] = {}
        export_evidence: dict[UUID, list[tuple[ExportRecord, list[ExportArtifactRecord]]]] = {}
        if chapter_ids:
            for import_job in session.scalars(
                select(ImageImportJobRecord)
                .where(ImageImportJobRecord.target_chapter_id.in_(chapter_ids))
                .order_by(ImageImportJobRecord.updated_at.desc())
            ):
                import_evidence.setdefault(import_job.target_chapter_id, []).append(import_job)
            for export_link, export in session.execute(
                select(ExportChapterRecord, ExportRecord)
                .join(ExportRecord, ExportRecord.id == ExportChapterRecord.export_id)
                .where(ExportChapterRecord.chapter_id.in_(chapter_ids))
                .order_by(ExportRecord.updated_at.desc())
            ):
                artifacts = list(
                    session.scalars(
                        select(ExportArtifactRecord)
                        .where(ExportArtifactRecord.export_id == export.id)
                        .order_by(ExportArtifactRecord.position)
                    )
                )
                export_evidence.setdefault(export_link.chapter_id, []).append((export, artifacts))

        entries: list[LibraryEntry] = []
        for manga, chapter in rows:
            if chapter is None:
                entries.append(
                    LibraryEntry(
                        manga_id=manga.id,
                        manga_title=manga.title,
                        author=manga.author,
                        manga_favorite=manga.favorite,
                        chapter_id=None,
                        chapter_title=None,
                        chapter_number=None,
                        volume=None,
                        chapter_position=None,
                        chapter_favorite=False,
                        availability=AvailabilityState.NOT_DOWNLOADED,
                        page_count=0,
                        page_total=None,
                        download_state=None,
                        export_state=None,
                        updated_at=_as_utc(manga.updated_at),
                        simulated=manga.simulated,
                    )
                )
                continue

            pages = pages_by_chapter.get(chapter.id, [])
            local_states = [
                _file_state(Path(page.original_path), page.source_sha256)
                for page in pages
            ]
            for page in pages:
                local_states.extend(
                    _file_state(Path(item.path), item.sha256)
                    for item in processed_by_page.get(page.id, [])
                )
            missing_file = any(state == "missing" for state in local_states)
            altered_file = any(state == "altered" for state in local_states)

            completed_download = False
            active_progress = 0
            page_total: int | None = None
            download_state: str | None = None
            latest_download_at: datetime | None = None
            for chapter_download, job in download_evidence.get(chapter.id, []):
                if download_state is None:
                    download_state = job.state
                    latest_download_at = _as_utc(job.updated_at)
                active_progress = max(active_progress, chapter_download.page_completed)
                if chapter_download.page_total is not None:
                    page_total = max(page_total or 0, chapter_download.page_total)
                stored_pages = download_pages.get((job.id, chapter.id), [])
                verified_download_pages = all(
                    item.state == "complete"
                    and item.original_path is not None
                    and item.sha256 is not None
                    and _file_state(Path(item.original_path), item.sha256) == "available"
                    for item in stored_pages
                )
                if (
                    job.state == "succeeded"
                    and chapter_download.state == "complete"
                    and chapter_download.page_total is not None
                    and chapter_download.page_total > 0
                    and chapter_download.page_completed == chapter_download.page_total
                    and len(stored_pages) == chapter_download.page_total
                    and verified_download_pages
                ):
                    completed_download = True
                    page_total = chapter_download.page_total
                    break

            complete_import = False
            latest_import_at: datetime | None = None
            for import_job in import_evidence.get(chapter.id, []):
                if latest_import_at is None:
                    latest_import_at = _as_utc(import_job.updated_at)
                if (
                    import_job.state == "succeeded"
                    and import_job.total_images > 0
                    and import_job.completed_images == import_job.total_images
                    and sum(page.import_job_id == import_job.id for page in pages)
                    == import_job.total_images
                ):
                    complete_import = True

            availability = classify_availability(
                AvailabilityEvidence(
                page_count=len(pages),
                complete_download=completed_download,
                expected_download_count=page_total,
                complete_import=complete_import,
                missing_file=missing_file,
                altered_file=altered_file,
                active_progress=active_progress,
                )
            )

            export_state: str | None = None
            latest_export_at: datetime | None = None
            for export, artifacts in export_evidence.get(chapter.id, []):
                if export_state is None:
                    export_state = export.state
                    latest_export_at = _as_utc(export.updated_at)
                if export.state == "completed":
                    for artifact in artifacts:
                        state = _file_state(Path(artifact.path), artifact.sha256)
                        if state == "missing":
                            export_state = "missing"
                        elif state == "altered":
                            export_state = "altered"

            activity_dates = [
                _as_utc(manga.updated_at),
                _as_utc(chapter.created_at),
                latest_download_at,
                latest_import_at,
                latest_export_at,
            ]
            updated_at = max(date for date in activity_dates if date is not None)
            entries.append(
                LibraryEntry(
                    manga_id=manga.id,
                    manga_title=manga.title,
                    author=manga.author,
                    manga_favorite=manga.favorite,
                    chapter_id=chapter.id,
                    chapter_title=chapter.title,
                    chapter_number=chapter.number,
                    volume=chapter.volume,
                    chapter_position=chapter.position,
                    chapter_favorite=chapter.favorite,
                    availability=availability,
                    page_count=len(pages),
                    page_total=page_total,
                    download_state=download_state,
                    export_state=export_state,
                    updated_at=updated_at,
                    simulated=manga.simulated,
                )
            )
        return entries


def _classify_entry(
    *,
    page_count: int,
    complete_download: bool,
    page_total: int | None,
    complete_import: bool,
    missing_file: bool,
    altered_file: bool,
    active_progress: int,
) -> AvailabilityState:
    if altered_file:
        return AvailabilityState.ALTERED
    if missing_file:
        return AvailabilityState.MISSING
    if complete_download and page_total is not None and page_count >= page_total:
        return AvailabilityState.DOWNLOADED
    if complete_import and page_count > 0:
        return AvailabilityState.IMPORTED
    if page_count > 0 or active_progress > 0:
        return AvailabilityState.PARTIAL
    return AvailabilityState.NOT_DOWNLOADED


def _file_state(path: Path, expected_hash: str | None) -> str:
    try:
        if path.is_symlink() or not path.is_file():
            return "missing"
        if expected_hash is None:
            return "available"
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return "available" if digest.hexdigest() == expected_hash else "altered"
    except OSError:
        return "missing"


def _inspect_file(path: Path, expected_hash: str | None = None) -> tuple[str | None, int, str]:
    if path.is_symlink() or not path.is_file():
        return None, 0, "missing"
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError:
        return None, 0, "missing"
    actual_hash = digest.hexdigest()
    state = "altered" if expected_hash is not None and expected_hash != actual_hash else "available"
    return actual_hash, size, state


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.absolute())).casefold()


def _is_managed_path(path: Path, roots: tuple[Path, ...]) -> bool:
    candidate = Path(os.path.abspath(path))
    for root in roots:
        try:
            relative = candidate.relative_to(root)
        except ValueError:
            continue
        current = root
        if current.is_symlink():
            return False
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return False
        try:
            return candidate.resolve(strict=False).is_relative_to(root.resolve(strict=False))
        except OSError:
            return False
    return False


def _orphan_asset(
    record: LibraryAssetRecord,
    managed_roots: tuple[Path, ...],
) -> LibraryAsset:
    expected_hash = record.sha256 or None
    _actual_hash, actual_size, actual_state = _inspect_file(Path(record.path), expected_hash)
    state = {
        "available": LibraryAssetState.UNLINKED,
        "missing": LibraryAssetState.MISSING,
        "altered": LibraryAssetState.CHANGED,
    }[actual_state]
    return LibraryAsset(
        id=f"orphan:{record.id}",
        category=LibraryAssetCategory(record.category),
        path=Path(record.path),
        sha256=record.sha256,
        size_bytes=actual_size if actual_state == "available" else record.size_bytes,
        media_type=record.media_type,
        managed=_is_managed_path(Path(record.path), managed_roots),
        state=state,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _identity(manga_title: str | None, chapter: ChapterRecord | None) -> str:
    if manga_title is None:
        return "Registro sem vínculo"
    if chapter is None:
        return manga_title
    chapter_title = chapter.title or f"Capítulo {chapter.number or ''}".strip()
    return f"{manga_title} — {chapter_title}"


def _import_identity(
    import_job: ImageImportJobRecord,
    manga: MangaRecord | None,
    chapter: ChapterRecord | None,
) -> str:
    if manga is not None and chapter is not None:
        return _identity(manga.title, chapter)
    manga_title = import_job.manga_title_snapshot
    chapter_title = import_job.chapter_title_snapshot
    if manga_title is not None and chapter_title is not None:
        return f"{manga_title} — {chapter_title}"
    return _identity(manga.title if manga is not None else None, chapter)


def _snapshot_chapter_count(snapshot: dict[str, object]) -> int:
    value = snapshot.get("chapter_count", 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _export_identity(snapshot: dict[str, object], chapter_count: int) -> str:
    items = snapshot.get("items")
    if isinstance(items, list):
        identities = []
        for item in items:
            if not isinstance(item, dict):
                continue
            manga_title = item.get("manga_title")
            chapter_title = item.get("chapter_title")
            chapter_number = item.get("chapter_number")
            if not isinstance(manga_title, str):
                continue
            item_title = chapter_title if isinstance(chapter_title, str) and chapter_title else None
            if item_title is None and isinstance(chapter_number, str) and chapter_number:
                item_title = f"Capítulo {chapter_number}"
            if item_title is not None:
                identities.append(f"{manga_title} — {item_title}")
            else:
                identities.append(manga_title)
        if identities:
            return "; ".join(identities)
    suffix = "capítulo" if chapter_count == 1 else "capítulos"
    return f"{chapter_count} {suffix}"
