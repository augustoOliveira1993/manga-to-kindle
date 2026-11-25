"""Ordenação canônica por metadado numérico, sem analisar títulos livres."""

from __future__ import annotations

from collections.abc import Sequence

from manga_to_kindle.domain.chapter import Chapter


def order_chapters(chapters: Sequence[Chapter]) -> tuple[Chapter, ...]:
    """Ordena números primeiro; especiais usam sequência da fonte e depois ID estável."""

    return tuple(
        sorted(
            chapters,
            key=lambda chapter: (
                chapter.number is None,
                chapter.number if chapter.number is not None else 0,
                chapter.source_order is None,
                chapter.source_order if chapter.source_order is not None else 0,
                str(chapter.id),
            ),
        )
    )
