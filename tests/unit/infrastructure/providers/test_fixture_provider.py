from __future__ import annotations

import socket

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.providers import MangaProvider
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_fixture_provider_is_deterministic_and_never_resolves_or_connects(monkeypatch) -> None:
    def reject(*_args, **_kwargs):
        raise AssertionError("fixture attempted network access")

    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)
    provider = FixtureProvider()
    url = normalize_url("https://fixture.invalid/manga/demo")

    assert isinstance(provider, MangaProvider)
    manga = provider.get_manga(url)
    chapters = provider.get_chapters(manga)
    pages = provider.get_pages(chapters[0])
    again = provider.get_manga(url)

    assert manga.id == again.id
    assert manga.chapters == provider.get_chapters(again)
    assert all(chapter.manga_id == manga.id for chapter in chapters)
    assert [page.position for page in pages] == list(range(len(pages)))
    assert all(page.simulated for page in pages)
    assert provider.capabilities.download_authorized is False
