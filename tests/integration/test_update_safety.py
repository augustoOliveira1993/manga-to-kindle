from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select

from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.updates.refresh_manga_catalog import RefreshMangaCatalog
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    ChapterCatalogResponse,
    ContentUnavailable,
    NormalizedUrl,
    ProviderCapabilities,
    ProviderPageReference,
)
from manga_to_kindle.domain.updates import UpdateCheck, UpdateCheckStatus
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    DownloadJobRecord,
    ExportRecord,
    TransferJobRecord,
)
from manga_to_kindle.infrastructure.persistence.update_repository import UpdateRepository

MANGA_ID = UUID("79d8738e-6bb1-401c-becd-4b54eea9d83c")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class LocalContractProvider:
    provider_id = "authorized-test-contract"
    capabilities = ProviderCapabilities(
        provider_id=provider_id,
        allowed_hosts=frozenset({"metadata.test"}),
        metadata=True,
        chapters=True,
        requests_per_minute=1,
        catalog_query_authorized=True,
        catalog_query_evidence="test-only:manual-contract",
        catalog_query_reviewed_on=date(2026, 1, 1),
        catalog_query_scope="isolated application contract test",
    )

    def __init__(self) -> None:
        self.response = ChapterCatalogResponse(
            (
                Chapter(
                    manga_id=MANGA_ID,
                    id=uuid4(),
                    position=0,
                    title="Capítulo 1",
                    number=Decimal("1"),
                    source_chapter_id="test:chapter-1",
                ),
                Chapter(
                    manga_id=MANGA_ID,
                    id=uuid4(),
                    position=1,
                    title="Capítulo novo",
                    number=Decimal("2"),
                    source_chapter_id="test:chapter-2",
                ),
            ),
            complete=True,
        )

    def supports(self, url: NormalizedUrl) -> bool:
        return url.host == "metadata.test"

    def get_manga(self, url: NormalizedUrl) -> Manga:
        raise AssertionError("O refresh usa somente o mangá persistido.")

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        raise AssertionError("F010 precisa de resposta completa explícita.")

    def get_chapter_catalog(
        self,
        manga: Manga,
        *,
        is_cancelled=None,
    ) -> ChapterCatalogResponse:
        return self.response

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        raise ContentUnavailable()


def test_new_chapter_notice_never_creates_download_export_or_transfer_job(tmp_path) -> None:
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    old_chapter = Chapter(
        manga_id=MANGA_ID,
        position=0,
        title="Capítulo 1",
        number=Decimal("1"),
        source_chapter_id="test:chapter-1",
    )
    initial = CatalogSnapshot(
        provider_id=LocalContractProvider.provider_id,
        source_id="contract-test:series",
        manga=Manga(
            id=MANGA_ID,
            title="Série de teste",
            source_ref="contract-test:series",
            chapters=(old_chapter,),
        ),
        updated_at=NOW,
        simulated=False,
    )
    catalog = CatalogRepository(database)
    catalog.replace(initial)
    updates = UpdateRepository(database)
    updates.commit_snapshot(
        initial,
        UpdateCheck(
            manga_id=MANGA_ID,
            provider_id=initial.provider_id,
            started_at=NOW,
            finished_at=NOW,
            status=UpdateCheckStatus.SUCCEEDED,
            chapter_count=1,
        ),
        (),
    )
    provider = LocalContractProvider()
    current_time = [NOW + timedelta(minutes=1)]
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: current_time[0],
    )
    try:
        result = refresh.execute(MANGA_ID)
        assert len(result.notices) == 1
        assert result.notices[0].source_chapter_id == "test:chapter-2"
        with database.unit_of_work() as session:
            counts = (
                session.scalar(select(func.count()).select_from(DownloadJobRecord)),
                session.scalar(select(func.count()).select_from(ExportRecord)),
                session.scalar(select(func.count()).select_from(TransferJobRecord)),
            )
        assert counts == (0, 0, 0)
    finally:
        database.close()
