"""Provider determinístico de demonstração para o host sintético fixture.invalid."""

from __future__ import annotations

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.domain.providers import (
    ContentUnavailable,
    NormalizedUrl,
    ProviderCapabilities,
    ProviderPageReference,
    UnsupportedSource,
)

_MANGA_ID = UUID("42a1d674-c3f4-5c17-9240-1efbd886e5fd")
_CHAPTERS: tuple[tuple[str, str | None, str, int | None], ...] = (
    ("demo-010", "10", "Capítulo 10 — Demonstração", 5),
    ("demo-special-b", None, "Bônus B — Demonstração", 7),
    ("demo-001", "1", "Capítulo 1 — Demonstração", 1),
    ("demo-001-extra", "1", "Capítulo 1 extra — Demonstração", 2),
    ("demo-001-5", "1.5", "Capítulo 1.5 — Demonstração", 3),
    ("demo-002", "2", "Capítulo 2 — Demonstração", 4),
    ("demo-special-a", None, "Bônus A — Demonstração", 6),
)


class FixtureProvider:
    provider_id = "fixture"

    def __init__(self) -> None:
        self.capabilities = ProviderCapabilities(
            provider_id=self.provider_id,
            allowed_hosts=frozenset({"fixture.invalid"}),
            allowed_ports=frozenset({443}),
            allowed_schemes=frozenset({"https"}),
            metadata=True,
            chapters=True,
            page_references=True,
            simulated=True,
            download_authorized=False,
            required_attribution="Dados fictícios internos do Manga to Kindle.",
            removal_policy="Remova a fixture quando ela deixar de ser necessária nos testes.",
        )

    def supports(self, url: NormalizedUrl) -> bool:
        return url.scheme == "https" and url.host == "fixture.invalid" and url.path == "/manga/demo"

    def get_manga(self, url: NormalizedUrl) -> Manga:
        if not self.supports(url):
            raise UnsupportedSource()
        chapters = self.get_chapters(
            Manga(title="A Biblioteca das Estrelas", id=_MANGA_ID, source_ref="fixture:demo")
        )
        return Manga(
            title="A Biblioteca das Estrelas",
            id=_MANGA_ID,
            source_ref="fixture:demo",
            chapters=chapters,
        )

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]:
        if manga.id != _MANGA_ID:
            raise ContentUnavailable()
        return tuple(
            Chapter(
                manga_id=_MANGA_ID,
                id=uuid5(NAMESPACE_URL, f"manga-to-kindle:fixture:chapter:{source_id}"),
                position=position,
                title=title,
                number=Decimal(number) if number is not None else None,
                source_order=source_order,
            )
            for position, (source_id, number, title, source_order) in enumerate(_CHAPTERS)
        )

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]:
        source_id = next(
            (
                source_id
                for source_id, _number, _title, _source_order in _CHAPTERS
                if chapter.id
                == uuid5(NAMESPACE_URL, f"manga-to-kindle:fixture:chapter:{source_id}")
                and chapter.manga_id == _MANGA_ID
            ),
            None,
        )
        if source_id is None:
            raise ContentUnavailable()
        return tuple(
            ProviderPageReference(
                source_id=f"{source_id}-page-{page_position:03d}",
                position=page_position,
                source_reference=f"fixture:{source_id}:{page_position}",
                destination=normalize_url(
                    f"https://fixture.invalid/pages/{source_id}/{page_position:03d}.webp"
                ),
                simulated=True,
            )
            for page_position in range(3)
        )


def build_fixture_provider() -> FixtureProvider:
    """Cria uma instância sem estado e sem efeitos colaterais."""

    return FixtureProvider()
