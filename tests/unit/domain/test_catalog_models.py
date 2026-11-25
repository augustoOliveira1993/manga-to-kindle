from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.manga import Manga


def test_snapshot_preserves_absent_optional_metadata() -> None:
    manga_id = uuid4()
    chapter = Chapter(
        manga_id=manga_id,
        id=uuid4(),
        position=0,
        title="Capítulo 1",
        number=Decimal("1"),
    )
    snapshot = CatalogSnapshot(
        provider_id="fixture",
        source_id="fixture:demo",
        manga=Manga(id=manga_id, title="Exemplo", chapters=(chapter,)),
        updated_at=datetime.now(UTC),
        simulated=True,
    )

    assert snapshot.manga.author is None
    assert snapshot.manga.cover_path is None
    assert snapshot.manga.language is None
    assert snapshot.chapters == (chapter,)


def test_snapshot_rejects_unstable_identity_or_naive_timestamp() -> None:
    manga_id = uuid4()
    chapter = Chapter(manga_id=manga_id, position=0, title="Capítulo especial")
    manga = Manga(id=manga_id, title="Exemplo", chapters=(chapter,))

    with pytest.raises(DomainValidationError):
        CatalogSnapshot(
            provider_id="",
            source_id="fixture:demo",
            manga=manga,
            updated_at=datetime.now(UTC),
            simulated=True,
        )
    with pytest.raises(DomainValidationError):
        CatalogSnapshot(
            provider_id="fixture",
            source_id="fixture:demo",
            manga=manga,
            updated_at=datetime.now(),
            simulated=True,
        )
