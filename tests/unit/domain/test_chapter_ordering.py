from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.chapter_ordering import order_chapters


def _chapter(identity: int, number: str | None, source_order: int | None) -> Chapter:
    return Chapter(
        manga_id=UUID(int=1),
        id=UUID(int=identity),
        position=identity,
        title=f"Capítulo {number}" if number else f"Especial {identity}",
        number=Decimal(number) if number else None,
        source_order=source_order,
    )


def test_order_is_numeric_decimal_then_special_and_stable() -> None:
    chapters = (
        _chapter(10, "10", 4),
        _chapter(6, None, 6),
        _chapter(1, "1", 1),
        _chapter(15, "1.5", 2),
        _chapter(2, "2", 3),
        _chapter(7, None, 7),
    )

    ordered = order_chapters(chapters)

    assert [chapter.number for chapter in ordered] == [
        Decimal("1"),
        Decimal("1.5"),
        Decimal("2"),
        Decimal("10"),
        None,
        None,
    ]
    assert [chapter.id for chapter in ordered[-2:]] == [UUID(int=6), UUID(int=7)]


def test_numeric_ties_use_source_order_then_stable_identity() -> None:
    chapters = (
        _chapter(20, "2", None),
        _chapter(12, "2", 2),
        _chapter(11, "2", 1),
    )

    assert [chapter.id for chapter in order_chapters(chapters)] == [
        UUID(int=11),
        UUID(int=12),
        UUID(int=20),
    ]
