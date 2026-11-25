from __future__ import annotations

from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_fixture_exposes_metadata_without_granting_download_permission() -> None:
    provider = FixtureProvider()

    assert provider.capabilities.metadata
    assert provider.capabilities.chapters
    assert provider.capabilities.page_references
    assert not provider.capabilities.download_authorized
    assert not provider.capabilities.download_enabled
