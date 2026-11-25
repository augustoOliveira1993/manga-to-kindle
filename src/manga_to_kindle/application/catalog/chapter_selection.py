"""Seleção por IDs estáveis, independente da posição visual persistida."""

from __future__ import annotations

from uuid import UUID


class ChapterSelection:
    def __init__(self) -> None:
        self._selected_ids: set[UUID] = set()

    @property
    def selected_ids(self) -> frozenset[UUID]:
        return frozenset(self._selected_ids)

    def select(self, chapter_id: UUID) -> None:
        self._selected_ids.add(chapter_id)

    def deselect(self, chapter_id: UUID) -> None:
        self._selected_ids.discard(chapter_id)

    def select_range(
        self,
        first_id: UUID,
        last_id: UUID,
        ordered_ids: tuple[UUID, ...],
    ) -> None:
        positions = {chapter_id: index for index, chapter_id in enumerate(ordered_ids)}
        if first_id not in positions or last_id not in positions:
            raise KeyError("Os extremos precisam existir na ordem atual do catálogo.")
        start, end = sorted((positions[first_id], positions[last_id]))
        self._selected_ids.update(ordered_ids[start : end + 1])

    def reconcile(self, ordered_ids: tuple[UUID, ...]) -> None:
        present = set(ordered_ids)
        self._selected_ids.intersection_update(present)

    def replace(self, selected_ids: tuple[UUID, ...]) -> None:
        self._selected_ids = set(selected_ids)
