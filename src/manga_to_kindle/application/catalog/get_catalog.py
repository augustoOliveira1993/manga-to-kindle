"""Consulta e valida um catálogo completo através do registro F003."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.providers.resolve_provider import resolve_provider
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter_ordering import order_chapters
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.providers import (
    CapabilityUnavailable,
    MangaProvider,
    ProviderResponseInvalid,
)


class GetCatalog:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        value: str,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> CatalogSnapshot:
        cancelled = is_cancelled or (lambda: False)
        if cancelled():
            raise CatalogRefreshCancelled("A consulta foi cancelada.")
        resolved = resolve_provider(value, self._registry)
        provider: MangaProvider = resolved.provider
        if not provider.capabilities.metadata or not provider.capabilities.chapters:
            raise CapabilityUnavailable()
        try:
            manga = provider.get_manga(resolved.url)
            ordered_chapters = order_chapters(tuple(provider.get_chapters(manga)))
            if cancelled():
                raise CatalogRefreshCancelled("A consulta foi cancelada.")
            chapters = tuple(
                replace(chapter, position=position)
                for position, chapter in enumerate(ordered_chapters)
            )
            manga = replace(manga, chapters=chapters)
            source_id = manga.source_ref
            if source_id is None:
                raise ProviderResponseInvalid()
            return CatalogSnapshot(
                provider_id=provider.provider_id,
                source_id=source_id,
                manga=manga,
                updated_at=datetime.now(UTC),
                simulated=provider.capabilities.simulated,
            )
        except CatalogRefreshCancelled:
            raise
        except (AttributeError, DomainValidationError, TypeError, ValueError):
            raise ProviderResponseInvalid() from None
