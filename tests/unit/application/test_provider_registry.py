from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import pytest

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.providers.resolve_provider import resolve_provider
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    AmbiguousProvider,
    ProviderCapabilities,
    ProviderPageReference,
    UnsafeDestination,
    UnsupportedSource,
)
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


@dataclass(frozen=True)
class _ClaimingProvider:
    provider_id: str
    capabilities: ProviderCapabilities

    def supports(self, url) -> bool:
        return url.host == "fixture.invalid"

    def get_manga(self, url) -> Manga:
        return Manga(title=self.provider_id, id=UUID(int=1))

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        return (Chapter(manga_id=manga.id, position=0, title="1", number=Decimal(1)),)

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        return ()


def test_registry_selects_fixture_without_network() -> None:
    registry = ProviderRegistry([FixtureProvider()])

    resolved = resolve_provider("https://FIXTURE.invalid/manga/demo#capitulo", registry)

    assert resolved.provider.provider_id == "fixture"
    assert resolved.url.host == "fixture.invalid"


def test_registry_distinguishes_no_match_and_ambiguity() -> None:
    fixture = FixtureProvider()
    registry = ProviderRegistry([fixture])
    with pytest.raises(UnsupportedSource):
        registry.resolve(normalize_url("https://unknown.example/manga"))

    second = _ClaimingProvider(
        provider_id="second",
        capabilities=ProviderCapabilities(
            provider_id="second", allowed_hosts=frozenset({"fixture.invalid"})
        ),
    )
    with pytest.raises(AmbiguousProvider):
        ProviderRegistry([fixture, second]).resolve(
            normalize_url("https://fixture.invalid/manga/demo")
        )


def test_declared_nonstandard_port_is_required() -> None:
    with pytest.raises(UnsafeDestination):
        ProviderRegistry([FixtureProvider()]).resolve(
            normalize_url("https://fixture.invalid:8443/manga/demo")
        )
