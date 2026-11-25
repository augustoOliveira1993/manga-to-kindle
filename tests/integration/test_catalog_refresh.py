from __future__ import annotations

import pytest

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import (
    CatalogRefreshCancelled,
    RefreshCatalog,
)
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.providers import ProviderUnavailable
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_refresh_failure_and_cancellation_preserve_previous_snapshot(tmp_path) -> None:
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    repository = CatalogRepository(database)
    query = GetCatalog(ProviderRegistry([FixtureProvider()]))
    refresh = RefreshCatalog(query, repository)
    url = "https://fixture.invalid/manga/demo"

    saved = refresh.execute(url)

    class FailingQuery:
        def execute(self, _url: str):
            raise ProviderUnavailable()

    with pytest.raises(ProviderUnavailable):
        RefreshCatalog(FailingQuery(), repository).execute(url)
    with pytest.raises(CatalogRefreshCancelled):
        refresh.execute(url, is_cancelled=lambda: True)

    assert repository.get(saved.manga.id) == saved
    database.close()


def test_catalog_snapshot_survives_database_reopen(tmp_path) -> None:
    database_path = AppPaths.from_root(tmp_path).database_file
    database = SQLiteDatabase(database_path)
    database.initialize()
    repository = CatalogRepository(database)
    snapshot = GetCatalog(ProviderRegistry([FixtureProvider()])).execute(
        "https://fixture.invalid/manga/demo"
    )
    repository.replace(snapshot)
    database.close()

    reopened = SQLiteDatabase(database_path)
    reopened.initialize()
    restored = CatalogRepository(reopened).get(snapshot.manga.id)

    assert restored is not None
    assert restored.manga.id == snapshot.manga.id
    assert restored.chapters == snapshot.chapters
    assert restored.simulated
    reopened.close()
