from __future__ import annotations

from uuid import UUID

import pytest

from manga_to_kindle.application.catalog.chapter_selection import ChapterSelection


def test_range_selection_is_inclusive_and_normalizes_reversed_extremes() -> None:
    ids = tuple(UUID(int=value) for value in range(1, 6))
    selection = ChapterSelection()
    selection.select(ids[0])
    selection.select(ids[4])
    selection.select_range(ids[3], ids[1], ids)

    assert selection.selected_ids == frozenset(ids[1:4])


def test_selection_reconciles_stable_ids_after_catalog_refresh() -> None:
    ids = tuple(UUID(int=value) for value in range(1, 5))
    selection = ChapterSelection()
    selection.select(ids[0])
    selection.select(ids[2])
    selection.reconcile((ids[0], ids[1], ids[3]))

    assert selection.selected_ids == frozenset({ids[0]})
    with pytest.raises(KeyError):
        selection.select_range(ids[0], ids[2], (ids[0], ids[1], ids[3]))
