from __future__ import annotations

import socket
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.updates.preferences import SaveUpdatePreference
from manga_to_kindle.application.updates.refresh_manga_catalog import (
    RefreshMangaCatalog,
    UpdateTrigger,
)
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.library import LibraryQuery
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    CapabilityUnavailable,
    ChapterCatalogResponse,
    ContentUnavailable,
    NormalizedUrl,
    ProviderCapabilities,
    ProviderPageReference,
    ProviderResponseInvalid,
    RateLimited,
)
from manga_to_kindle.domain.updates import UpdatePreference
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.library_repository import LibraryRepository
from manga_to_kindle.infrastructure.persistence.update_repository import UpdateRepository

MANGA_ID = UUID("37a5b8c6-c67d-48d0-977e-fc6ea81a34fd")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class ContractProvider:
    provider_id = "metadata-provider"

    def __init__(
        self,
        response: ChapterCatalogResponse,
        *,
        authorized: bool = True,
        periodic: bool = False,
    ) -> None:
        self.response = response
        self.calls = 0
        self.capabilities = ProviderCapabilities(
            provider_id=self.provider_id,
            allowed_hosts=frozenset({"updates.example"}),
            metadata=True,
            chapters=True,
            requests_per_minute=1,
            catalog_query_authorized=authorized,
            catalog_query_evidence="test-only:policy-contract",
            catalog_query_reviewed_on=date(2026, 1, 1),
            catalog_query_scope="test provider contract only",
            periodic_catalog_updates_authorized=periodic,
            minimum_catalog_update_interval_seconds=60 if periodic else None,
        )

    def supports(self, url: NormalizedUrl) -> bool:
        return url.host == "updates.example"

    def get_manga(self, url: NormalizedUrl) -> Manga:
        raise AssertionError("F010 usa a identidade local persistida, não uma URL nova.")

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        raise AssertionError("F010 exige o contrato completo get_chapter_catalog.")

    def get_chapter_catalog(
        self,
        manga: Manga,
        *,
        is_cancelled=None,
    ) -> ChapterCatalogResponse:
        self.calls += 1
        return self.response

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        raise ContentUnavailable()


def make_chapter(source_id: str, *, title: str, number: str, chapter_id=None) -> Chapter:
    return Chapter(
        manga_id=MANGA_ID,
        id=chapter_id or uuid4(),
        position=0,
        title=title,
        number=Decimal(number),
        source_order=0,
        source_chapter_id=source_id,
    )


def seed_snapshot(database: SQLiteDatabase, chapters: tuple[Chapter, ...]) -> CatalogSnapshot:
    snapshot = CatalogSnapshot(
        provider_id=ContractProvider.provider_id,
        source_id="metadata-provider:series-42",
        manga=Manga(
            id=MANGA_ID,
            title="Série sob revisão",
            source_ref="metadata-provider:series-42",
            chapters=chapters,
        ),
        updated_at=NOW - timedelta(days=1),
        simulated=False,
    )
    CatalogRepository(database).replace(snapshot)
    return snapshot


def build_database(tmp_path) -> SQLiteDatabase:
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    return database


def test_authorized_metadata_refresh_is_atomic_and_notices_only_new_stable_ids(
    tmp_path,
    monkeypatch,
) -> None:
    def reject_network(*_args, **_kwargs) -> None:
        raise AssertionError("O adapter de contrato não deve abrir sockets.")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    database = build_database(tmp_path)
    previous_chapter_id = uuid4()
    existing = make_chapter(
        "provider:chapter-1",
        title="Nome anterior",
        number="1",
        chapter_id=previous_chapter_id,
    )
    prior_snapshot = seed_snapshot(database, (existing,))
    baseline_chapters = (
        make_chapter(
            "provider:chapter-1",
            title="Nome atualizado",
            number="1",
        ),
        make_chapter("provider:chapter-2", title="Capítulo 2", number="2"),
    )
    provider = ContractProvider(ChapterCatalogResponse(baseline_chapters, complete=True))
    registry = ProviderRegistry((provider,))
    catalog = CatalogRepository(database)
    updates = UpdateRepository(database)
    now = [NOW]
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        registry,
        clock=lambda: now[0],
    )
    try:
        baseline = refresh.execute(MANGA_ID)
        assert baseline.check.new_chapter_count == 0
        assert baseline.notices == ()
        provider.response = ChapterCatalogResponse(
            (
                make_chapter(
                    "provider:chapter-1",
                    title="Nome atualizado",
                    number="1",
                ),
                make_chapter("provider:chapter-2", title="Capítulo 2", number="2"),
                make_chapter("provider:chapter-3", title="Capítulo 3", number="3"),
            ),
            complete=True,
        )
        now[0] += timedelta(minutes=1)
        result = refresh.execute(MANGA_ID)
        assert provider.calls == 2
        assert result.snapshot.simulated is False
        assert result.snapshot.chapters[0].id == previous_chapter_id
        assert result.snapshot.chapters[0].title == "Nome atualizado"
        assert result.check.new_chapter_count == 1
        assert result.check.policy_fingerprint is not None
        assert len(result.check.policy_fingerprint) == 64
        assert [notice.source_chapter_id for notice in result.notices] == ["provider:chapter-3"]
        assert catalog.get(MANGA_ID) == result.snapshot
        assert updates.latest_check(MANGA_ID) == result.check
        assert catalog.get(MANGA_ID) != prior_snapshot
        library_page = LibraryRepository(database).search(
            LibraryQuery(search_text="Série sob revisão")
        )
        assert {entry.chapter_title for entry in library_page.entries} >= {
            "Nome atualizado",
            "Capítulo 2",
            "Capítulo 3",
        }
    finally:
        database.close()


def test_partial_response_preserves_last_valid_catalog_and_records_sanitized_failure(
    tmp_path,
) -> None:
    database = build_database(tmp_path)
    prior_snapshot = seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    provider = ContractProvider(ChapterCatalogResponse((), complete=False))
    catalog = CatalogRepository(database)
    updates = UpdateRepository(database)
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    try:
        with pytest.raises(ProviderResponseInvalid):
            refresh.execute(MANGA_ID)
        assert provider.calls == 1
        assert catalog.get(MANGA_ID) == prior_snapshot
        check = updates.latest_check(MANGA_ID)
        assert check is not None
        assert check.status.value == "failed"
        assert check.safe_error_code == "PROVIDER_RESPONSE_INVALID"
        assert check.new_chapter_count == 0
    finally:
        database.close()


def test_cancellation_after_response_preserves_snapshot_and_records_attempt(tmp_path) -> None:
    database = build_database(tmp_path)
    prior_snapshot = seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    provider = ContractProvider(
        ChapterCatalogResponse(
            (
                make_chapter(
                    "provider:chapter-1",
                    title="Capítulo 1 revisado",
                    number="1",
                ),
                make_chapter("provider:chapter-2", title="Capítulo 2", number="2"),
            ),
            complete=True,
        )
    )
    catalog = CatalogRepository(database)
    updates = UpdateRepository(database)
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    cancellation_checks = 0

    def cancel_after_provider_returns() -> bool:
        nonlocal cancellation_checks
        cancellation_checks += 1
        return cancellation_checks >= 3

    try:
        with pytest.raises(CatalogRefreshCancelled):
            refresh.execute(MANGA_ID, is_cancelled=cancel_after_provider_returns)
        assert provider.calls == 1
        assert catalog.get(MANGA_ID) == prior_snapshot
        check = updates.latest_check(MANGA_ID)
        assert check is not None
        assert check.status.value == "cancelled"
        assert check.safe_error_code == "UPDATE_CANCELLED"
    finally:
        database.close()


def test_unapproved_or_simulated_sources_are_rejected_before_provider_call(tmp_path) -> None:
    database = build_database(tmp_path)
    prior_snapshot = seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    provider = ContractProvider(
        ChapterCatalogResponse((), complete=True),
        authorized=False,
    )
    catalog = CatalogRepository(database)
    updates = UpdateRepository(database)
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    try:
        with pytest.raises(CapabilityUnavailable):
            refresh.execute(MANGA_ID)
        assert provider.calls == 0
        assert catalog.get(MANGA_ID) == prior_snapshot
        assert updates.latest_check(MANGA_ID).status.value == "unsupported"
    finally:
        database.close()


def test_local_rpm_limit_prevents_repeated_manual_provider_requests(tmp_path) -> None:
    database = build_database(tmp_path)
    seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    provider = ContractProvider(
        ChapterCatalogResponse(
            (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
            complete=True,
        )
    )
    catalog = CatalogRepository(database)
    updates = UpdateRepository(database)
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    try:
        refresh.execute(MANGA_ID)
        with pytest.raises(RateLimited):
            refresh.execute(MANGA_ID)
        assert provider.calls == 1
    finally:
        database.close()


def test_local_rpm_limit_is_shared_between_manga_for_the_same_provider(tmp_path) -> None:
    database = build_database(tmp_path)
    seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    second_manga_id = UUID("620271d1-08ce-469a-a8f4-75ea4e1c7d72")
    second_snapshot = CatalogSnapshot(
        provider_id=ContractProvider.provider_id,
        source_id="metadata-provider:series-43",
        manga=Manga(
            id=second_manga_id,
            title="Outra série",
            source_ref="metadata-provider:series-43",
            chapters=(
                Chapter(
                    manga_id=second_manga_id,
                    position=0,
                    title="Capítulo 1",
                    number=Decimal("1"),
                    source_chapter_id="provider:other-chapter-1",
                ),
            ),
        ),
        updated_at=NOW - timedelta(days=1),
        simulated=False,
    )
    catalog = CatalogRepository(database)
    catalog.replace(second_snapshot)
    provider = ContractProvider(
        ChapterCatalogResponse(
            (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
            complete=True,
        )
    )
    updates = UpdateRepository(database)
    refresh = RefreshMangaCatalog(
        catalog,
        updates,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    try:
        refresh.execute(MANGA_ID)
        with pytest.raises(RateLimited):
            refresh.execute(second_manga_id)
        assert provider.calls == 1
        assert catalog.get(second_manga_id) == second_snapshot
    finally:
        database.close()


def test_periodic_opt_in_needs_real_provider_policy_and_documented_minimum(tmp_path) -> None:
    database = build_database(tmp_path)
    seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    repository = UpdateRepository(database)
    provider = ContractProvider(
        ChapterCatalogResponse((), complete=True),
        periodic=False,
    )
    save = SaveUpdatePreference(
        CatalogRepository(database),
        repository,
        ProviderRegistry((provider,)),
        clock=lambda: NOW,
    )
    try:
        with pytest.raises(CapabilityUnavailable):
            save.execute(UpdatePreference(manga_id=MANGA_ID, enabled=True, interval_seconds=60))
        assert repository.get_preference(MANGA_ID).enabled is False
    finally:
        database.close()


def test_scheduled_update_respects_per_manga_opt_in_and_source_minimum(tmp_path) -> None:
    database = build_database(tmp_path)
    seed_snapshot(
        database,
        (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
    )
    repository = UpdateRepository(database)
    provider = ContractProvider(
        ChapterCatalogResponse(
            (make_chapter("provider:chapter-1", title="Capítulo 1", number="1"),),
            complete=True,
        ),
        periodic=True,
    )
    registry = ProviderRegistry((provider,))
    save = SaveUpdatePreference(
        CatalogRepository(database),
        repository,
        registry,
        clock=lambda: NOW - timedelta(minutes=10),
    )
    refresh = RefreshMangaCatalog(
        CatalogRepository(database),
        repository,
        registry,
        clock=lambda: NOW,
    )
    try:
        save.execute(UpdatePreference(manga_id=MANGA_ID, enabled=True, interval_seconds=120))
        result = refresh.execute(MANGA_ID, trigger=UpdateTrigger.SCHEDULED)
        assert provider.calls == 1
        assert result.check.status.value == "succeeded"
    finally:
        database.close()


def test_preferences_cannot_opt_into_monitoring_for_demo_fixture(tmp_path) -> None:
    database = build_database(tmp_path)
    demo_manga_id = UUID("42a1d674-c3f4-5c17-9240-1efbd886e5fd")
    from manga_to_kindle.application.catalog.get_catalog import GetCatalog
    from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
    from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider

    fixture = FixtureProvider()
    snapshot = GetCatalog(ProviderRegistry((fixture,))).execute(
        "https://fixture.invalid/manga/demo"
    )
    RefreshCatalog(GetCatalog(ProviderRegistry((fixture,))), CatalogRepository(database)).execute(
        "https://fixture.invalid/manga/demo"
    )
    repository = UpdateRepository(database)
    save = SaveUpdatePreference(
        CatalogRepository(database),
        repository,
        ProviderRegistry((fixture,)),
        clock=lambda: NOW,
    )
    try:
        assert snapshot.manga.id == demo_manga_id
        with pytest.raises(CapabilityUnavailable):
            save.execute(
                UpdatePreference(
                    manga_id=demo_manga_id,
                    enabled=True,
                    interval_seconds=60,
                )
            )
        assert repository.get_preference(demo_manga_id).enabled is False
    finally:
        database.close()
