"""Validação de opt-in periódico perante a política da fonte."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.providers import CapabilityUnavailable
from manga_to_kindle.domain.updates import UpdatePreference


class CatalogReader(Protocol):
    def get(self, manga_id: UUID) -> CatalogSnapshot | None: ...


class PreferenceWriter(Protocol):
    def save_preference(self, preference: UpdatePreference) -> UpdatePreference: ...


class SaveUpdatePreference:
    def __init__(
        self,
        catalog: CatalogReader,
        repository: PreferenceWriter,
        providers: ProviderRegistry,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._catalog = catalog
        self._repository = repository
        self._providers = providers
        self._clock = clock

    def execute(self, preference: UpdatePreference) -> UpdatePreference:
        if preference.enabled:
            snapshot: CatalogSnapshot | None = self._catalog.get(preference.manga_id)
            if snapshot is None or snapshot.simulated:
                raise CapabilityUnavailable()
            provider = self._providers.by_id(snapshot.provider_id)
            minimum = provider.capabilities.minimum_catalog_update_interval_seconds
            if (
                not provider.capabilities.periodic_catalog_updates_enabled
                or minimum is None
                or preference.interval_seconds is None
                or preference.interval_seconds < minimum
            ):
                raise CapabilityUnavailable()
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("O relógio da aplicação precisa retornar horário com fuso.")
        return self._repository.save_preference(replace(preference, updated_at=now.astimezone(UTC)))
