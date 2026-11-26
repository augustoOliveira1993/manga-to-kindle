from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import ProviderResponseInvalid, UnsupportedSource
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_get_catalog_uses_provider_fixture_and_marks_simulated() -> None:
    service = GetCatalog(ProviderRegistry([FixtureProvider()]))

    snapshot = service.execute("https://fixture.invalid/manga/demo")

    assert snapshot.provider_id == "fixture"
    assert snapshot.source_id == "fixture:demo"
    assert snapshot.simulated
    assert len(snapshot.chapters) == 7
    assert [chapter.position for chapter in snapshot.chapters] == list(range(7))
    assert [chapter.number for chapter in snapshot.chapters] == [
        Decimal("1"),
        Decimal("1"),
        Decimal("1.5"),
        Decimal("2"),
        Decimal("10"),
        None,
        None,
    ]


def test_get_catalog_rejects_unregistered_source_without_fallback() -> None:
    service = GetCatalog(ProviderRegistry([FixtureProvider()]))

    with pytest.raises(UnsupportedSource):
        service.execute("https://manga.example.test/title")


def test_get_catalog_rejects_chapter_associated_with_another_manga() -> None:
    class InvalidFixtureProvider(FixtureProvider):
        def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
            return (Chapter(manga_id=UUID(int=99), position=0, title="Capítulo inválido"),)

    service = GetCatalog(ProviderRegistry([InvalidFixtureProvider()]))

    with pytest.raises(ProviderResponseInvalid):
        service.execute("https://fixture.invalid/manga/demo")
