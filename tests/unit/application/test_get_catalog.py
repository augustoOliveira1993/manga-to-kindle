from __future__ import annotations

import pytest

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.providers import UnsupportedSource
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_get_catalog_uses_provider_fixture_and_marks_simulated() -> None:
    service = GetCatalog(ProviderRegistry([FixtureProvider()]))

    snapshot = service.execute("https://fixture.invalid/manga/demo")

    assert snapshot.provider_id == "fixture"
    assert snapshot.source_id == "fixture:demo"
    assert snapshot.simulated
    assert len(snapshot.chapters) == 2


def test_get_catalog_rejects_unregistered_source_without_fallback() -> None:
    service = GetCatalog(ProviderRegistry([FixtureProvider()]))

    with pytest.raises(UnsupportedSource):
        service.execute("https://manga.example.test/title")
