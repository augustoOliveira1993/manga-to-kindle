"""Modelos imutáveis para conteúdo sintético mostrado pela interface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga


class DemoOutcome(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


def resolve_demo_outcome(value: object) -> DemoOutcome:
    try:
        return DemoOutcome(str(value))
    except ValueError:
        return DemoOutcome.SUCCESS


@dataclass(frozen=True, slots=True)
class DemoMarker:
    fixture_id: str
    simulated: bool = True
    label: str = "DADOS SIMULADOS"


@dataclass(frozen=True, slots=True)
class DemoCatalog:
    marker: DemoMarker
    manga: Manga
    chapters: tuple[Chapter, ...]


@dataclass(frozen=True, slots=True)
class DemoResult:
    simulated: bool
    summary: str


@dataclass(frozen=True, slots=True)
class ChapterSelection:
    chapter_ids: tuple[UUID, ...]

    @property
    def count(self) -> int:
        return len(self.chapter_ids)

