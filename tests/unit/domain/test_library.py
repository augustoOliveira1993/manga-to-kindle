from __future__ import annotations

import pytest

from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.library import (
    AvailabilityState,
    LibraryQuery,
    LibrarySort,
    normalize_search_text,
)


def test_search_normalization_ignores_case_and_diacritics() -> None:
    assert normalize_search_text("  CIDADE   de PAPÉL ") == "cidade de papel"
    assert normalize_search_text("ÁGATA") == "agata"


def test_library_query_rejects_invalid_pagination_and_filters() -> None:
    with pytest.raises(DomainValidationError):
        LibraryQuery(limit=0)
    with pytest.raises(DomainValidationError):
        LibraryQuery(offset=-1)
    with pytest.raises(DomainValidationError):
        LibraryQuery(availability="unknown")  # type: ignore[arg-type]


def test_library_query_defaults_are_local_and_bounded() -> None:
    query = LibraryQuery()

    assert query.favorite_only is False
    assert query.availability is None
    assert query.sort is LibrarySort.TITLE
    assert query.limit == 100
    assert AvailabilityState.IMPORTED.value == "imported"
