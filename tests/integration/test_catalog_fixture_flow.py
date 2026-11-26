from __future__ import annotations

import socket
from datetime import UTC, datetime
from uuid import UUID

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.catalog.refresh_catalog import RefreshCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import UnsupportedSource
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_fixture_catalog_is_persisted_without_network_and_rejects_other_hosts(
    tmp_path, monkeypatch
) -> None:
    def reject_network(*_args, **_kwargs) -> None:
        raise AssertionError("A consulta de fixture não pode abrir sockets")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    database = SQLiteDatabase(AppPaths.from_root(tmp_path).database_file)
    database.initialize()
    repository = CatalogRepository(database)
    existing = CatalogSnapshot(
        provider_id="local",
        source_id="local:owned",
        manga=Manga(
            title="Meu registro local",
            id=UUID("60de411f-5d4a-4b8c-8d76-a5cc03e652f1"),
            source_ref="local:owned",
        ),
        updated_at=datetime.now(UTC),
        simulated=False,
    )
    repository.replace(existing)
    refresh = RefreshCatalog(
        GetCatalog(ProviderRegistry((FixtureProvider(),))),
        repository,
    )
    try:
        snapshot = refresh.execute("https://fixture.invalid/manga/demo")

        assert repository.get(snapshot.manga.id) == snapshot
        assert repository.get(existing.manga.id) == existing
        try:
            refresh.execute("https://example.test/manga")
        except UnsupportedSource:
            pass
        else:
            raise AssertionError("Uma URL externa não pode usar dados de fixture")
        assert repository.get(snapshot.manga.id) == snapshot
        assert repository.get(existing.manga.id) == existing
    finally:
        database.close()
