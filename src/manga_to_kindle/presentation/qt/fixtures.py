"""Catálogo fixo e repetível para a demonstração offline."""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.presentation.qt.view_models import DemoCatalog, DemoMarker

DEMO_MANGA_ID = UUID("8c8355cc-5012-5b66-9454-b52ab11de943")


def build_demo_catalog() -> DemoCatalog:
    chapter_titles = (
        "O começo da jornada",
        "A cidade silenciosa",
        "Um novo aliado",
        "A travessia",
        "O primeiro desafio",
    )
    chapters = tuple(
        Chapter(
            manga_id=DEMO_MANGA_ID,
            id=uuid5(NAMESPACE_URL, f"manga-to-kindle:demo:chapter:{position}"),
            position=position - 1,
            title=title,
            number=Decimal(position),
        )
        for position, title in enumerate(chapter_titles, start=1)
    )
    return DemoCatalog(
        marker=DemoMarker(fixture_id="demo-manga-001"),
        manga=Manga(
            id=DEMO_MANGA_ID,
            title="A Biblioteca das Estrelas",
            chapters=chapters,
        ),
        chapters=chapters,
    )

