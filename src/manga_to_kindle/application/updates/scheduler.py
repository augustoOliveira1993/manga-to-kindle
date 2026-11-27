"""Agendador puro: escolhe um único refresh devido e nunca cria rajadas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from uuid import UUID

from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.providers import UnsupportedSource
from manga_to_kindle.domain.updates import UpdateMangaStatus


@dataclass(frozen=True, slots=True)
class ScheduledUpdate:
    manga_id: UUID
    provider_id: str


class PeriodicUpdateScheduler:
    """Mantém timers apenas no processo e coalesce verificações vencidas."""

    def __init__(self) -> None:
        self._in_flight_manga: set[UUID] = set()
        self._in_flight_providers: set[str] = set()
        self._provider_ready_at: dict[str, datetime] = {}

    def claim_due(
        self,
        statuses: tuple[UpdateMangaStatus, ...],
        providers: ProviderRegistry,
        now: datetime,
    ) -> ScheduledUpdate | None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("O scheduler exige um horário com fuso.")
        provider_latest: dict[str, datetime] = {}
        provider_retry_after: dict[str, datetime] = {}
        for status in statuses:
            if status.provider_id is None or status.last_check is None:
                continue
            latest = provider_latest.get(status.provider_id)
            if latest is None or status.last_check.started_at > latest:
                provider_latest[status.provider_id] = status.last_check.started_at
            retry_after = status.last_check.retry_after_at
            if retry_after is not None:
                latest_retry = provider_retry_after.get(status.provider_id)
                if latest_retry is None or retry_after > latest_retry:
                    provider_retry_after[status.provider_id] = retry_after
        candidates: list[tuple[datetime, UpdateMangaStatus, int]] = []
        for status in statuses:
            preference = status.preference
            provider_id = status.provider_id
            if (
                not preference.enabled
                or preference.interval_seconds is None
                or status.simulated
                or provider_id is None
                or status.manga_id in self._in_flight_manga
            ):
                continue
            try:
                provider = providers.by_id(provider_id)
            except UnsupportedSource:
                continue
            capabilities = provider.capabilities
            minimum = capabilities.minimum_catalog_update_interval_seconds
            requests_per_minute = capabilities.requests_per_minute
            if (
                not capabilities.periodic_catalog_updates_enabled
                or minimum is None
                or requests_per_minute is None
                or preference.interval_seconds < minimum
                or provider_id in self._in_flight_providers
            ):
                continue
            request_spacing = ceil(60 / requests_per_minute)
            effective_interval = max(
                minimum,
                preference.interval_seconds,
                request_spacing,
            )
            last_check = status.last_check
            reference = (
                last_check.started_at if last_check is not None else preference.updated_at or now
            )
            due_at = reference + timedelta(seconds=effective_interval)
            if last_check is not None and last_check.retry_after_at is not None:
                due_at = max(due_at, last_check.retry_after_at)
            last_provider_check = provider_latest.get(provider_id)
            if last_provider_check is not None:
                due_at = max(
                    due_at,
                    last_provider_check + timedelta(seconds=request_spacing),
                )
            provider_retry = provider_retry_after.get(provider_id)
            if provider_retry is not None:
                due_at = max(due_at, provider_retry)
            due_at = max(due_at, self._provider_ready_at.get(provider_id, due_at))
            if due_at <= now:
                candidates.append((due_at, status, request_spacing))
        if not candidates:
            return None
        _due_at, status, request_spacing = min(
            candidates,
            key=lambda item: (item[0], item[1].provider_id or "", str(item[1].manga_id)),
        )
        provider_id = status.provider_id
        if provider_id is None:
            return None
        self._in_flight_manga.add(status.manga_id)
        self._in_flight_providers.add(provider_id)
        self._provider_ready_at[provider_id] = now + timedelta(seconds=request_spacing)
        return ScheduledUpdate(status.manga_id, provider_id)

    def release(self, scheduled: ScheduledUpdate) -> None:
        self._in_flight_manga.discard(scheduled.manga_id)
        self._in_flight_providers.discard(scheduled.provider_id)
