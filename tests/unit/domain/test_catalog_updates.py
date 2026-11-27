from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.updates import (
    ConflictingChapterIdentity,
    UnstableChapterIdentity,
    UpdatePreference,
    reconcile_chapters,
)

MANGA_ID = UUID("0e298cae-3a12-4b7b-a6a4-8514e2ff514a")
UPDATE_FIXTURES = Path(__file__).parents[2] / "fixtures" / "updates"


def chapter(
    source_id: str | None,
    *,
    chapter_id: UUID | None = None,
    title: str = "Capítulo",
    number: str = "1",
    position: int = 0,
    source_order: int | None = 0,
) -> Chapter:
    return Chapter(
        manga_id=MANGA_ID,
        id=chapter_id or uuid4(),
        position=position,
        title=title,
        number=Decimal(number),
        source_order=source_order,
        source_chapter_id=source_id,
    )


def test_reconcile_uses_stable_source_id_and_preserves_local_chapter_id() -> None:
    existing_id = uuid4()
    old = chapter("provider:ch-1", chapter_id=existing_id, title="Antigo", number="1")
    updated = chapter(
        "provider:ch-1",
        chapter_id=uuid4(),
        title="Título revisado",
        number="1.5",
        position=8,
    )
    added = chapter("provider:ch-2", title="Novo", number="2", position=9)

    result = reconcile_chapters((old,), (added, updated))

    assert result.new_source_chapter_ids == ("provider:ch-2",)
    assert result.chapters[0].id == existing_id
    assert result.chapters[0].title == "Título revisado"
    assert result.chapters[0].position == 0
    assert result.chapters[1].source_chapter_id == "provider:ch-2"
    assert result.chapters[1].position == 1


def test_reconcile_coalesces_exact_duplicates_and_rejects_conflicts() -> None:
    first = chapter("provider:ch-1", title="Mesmo")
    duplicate = chapter(
        "provider:ch-1",
        chapter_id=uuid4(),
        title="Mesmo",
        position=4,
    )
    assert len(reconcile_chapters((), (first, duplicate)).chapters) == 1

    conflict = chapter(
        "provider:ch-1",
        chapter_id=uuid4(),
        title="Conflitante",
    )
    with pytest.raises(ConflictingChapterIdentity):
        reconcile_chapters((), (first, conflict))


def test_reconcile_requires_stable_ids_and_does_not_match_by_title_or_number() -> None:
    old = chapter("provider:ch-1", chapter_id=UUID(int=1), title="Mesmo", number="1")
    renamed_identity = chapter(
        "provider:ch-2",
        chapter_id=UUID(int=2),
        title="Mesmo",
        number="1",
    )

    result = reconcile_chapters((old,), (renamed_identity,))
    assert result.new_source_chapter_ids == ("provider:ch-2",)
    assert result.chapters[0].id == UUID(int=2)
    with pytest.raises(UnstableChapterIdentity):
        reconcile_chapters((), (chapter(None),))


def test_update_preference_is_disabled_by_default_and_validates_opt_in() -> None:
    preference = UpdatePreference(manga_id=MANGA_ID)
    assert not preference.enabled
    assert preference.interval_seconds is None
    with pytest.raises(DomainValidationError):
        UpdatePreference(manga_id=MANGA_ID, enabled=True)
    with pytest.raises(DomainValidationError):
        UpdatePreference(manga_id=MANGA_ID, interval_seconds=0)


def test_update_preference_validates_timestamp_offset() -> None:
    with pytest.raises(DomainValidationError):
        UpdatePreference(
            manga_id=MANGA_ID,
            updated_at=datetime(2026, 1, 1),
        )


def test_catalog_version_fixture_reconciles_only_new_stable_ids() -> None:
    fixture = json.loads(
        (UPDATE_FIXTURES / "catalog_versions.json").read_text(encoding="utf-8")
    )

    def from_fixture(records: list[dict[str, object]]) -> tuple[Chapter, ...]:
        return tuple(
            Chapter(
                manga_id=MANGA_ID,
                id=UUID(str(record["id"])),
                position=position,
                title=str(record["title"]),
                number=(
                    Decimal(str(record["number"]))
                    if record["number"] is not None
                    else None
                ),
                source_order=int(str(record["source_order"])),
                source_chapter_id=str(record["source_chapter_id"]),
            )
            for position, record in enumerate(records)
        )

    previous = from_fixture(fixture["previous"])
    incoming = from_fixture(fixture["incoming"])
    reconciliation = reconcile_chapters(previous, incoming)
    assert reconciliation.new_source_chapter_ids == tuple(fixture["expected_new_ids"])
    assert reconciliation.chapters[0].id == previous[0].id
    assert reconciliation.chapters[0].title == "Título revisado"
