"""Consulta autorizada e transacional de atualizações de catálogo F010."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import ceil
from typing import Protocol
from uuid import UUID

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.providers import (
    CapabilityUnavailable,
    CatalogUpdateProvider,
    ChapterCatalogResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCode,
    ProviderResponseInvalid,
    ProviderUnavailable,
    RateLimited,
    UnsupportedSource,
)
from manga_to_kindle.domain.updates import (
    ChapterNotice,
    UpdateCheck,
    UpdateCheckStatus,
    UpdatePreference,
    reconcile_chapters,
)


class UpdateTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class CatalogReader(Protocol):
    def get(self, manga_id: UUID) -> CatalogSnapshot | None: ...


class UpdateWriter(Protocol):
    def latest_check(self, manga_id: UUID) -> UpdateCheck | None: ...

    def latest_provider_check(self, provider_id: str) -> UpdateCheck | None: ...

    def has_successful_check(self, manga_id: UUID) -> bool: ...

    def get_preference(self, manga_id: UUID) -> UpdatePreference: ...

    def record_check(self, check: UpdateCheck) -> None: ...

    def commit_snapshot(
        self,
        snapshot: CatalogSnapshot,
        check: UpdateCheck,
        new_source_chapter_ids: tuple[str, ...],
    ) -> tuple[ChapterNotice, ...]: ...


@dataclass(frozen=True, slots=True)
class RefreshMangaCatalogResult:
    snapshot: CatalogSnapshot
    check: UpdateCheck
    notices: tuple[ChapterNotice, ...]


class RefreshMangaCatalog:
    """Atualiza apenas fontes não simuladas com autorização independente de download."""

    def __init__(
        self,
        catalog: CatalogReader,
        updates: UpdateWriter,
        providers: ProviderRegistry,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._catalog = catalog
        self._updates = updates
        self._providers = providers
        self._clock = clock

    def execute(
        self,
        manga_id: UUID,
        *,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> RefreshMangaCatalogResult:
        cancelled = is_cancelled or (lambda: False)
        previous = self._catalog.get(manga_id)
        if previous is None:
            raise UnsupportedSource()
        started_at = _aware_utc(self._clock())
        preference = self._updates.get_preference(manga_id)
        if cancelled():
            self._record_failure(
                previous,
                started_at,
                UpdateCheckStatus.CANCELLED,
                "UPDATE_CANCELLED",
            )
            raise CatalogRefreshCancelled("A atualização foi cancelada.")
        policy_fingerprint: str | None = None
        try:
            provider = self._providers.by_id(previous.provider_id)
            policy_fingerprint = _provider_policy_fingerprint(provider.capabilities)
            if previous.simulated or provider.capabilities.simulated:
                raise CapabilityUnavailable()
            if not provider.capabilities.catalog_query_enabled:
                raise CapabilityUnavailable()
            if trigger is UpdateTrigger.SCHEDULED:
                if not preference.enabled:
                    raise CapabilityUnavailable()
                if not provider.capabilities.periodic_catalog_updates_enabled:
                    raise CapabilityUnavailable()
                minimum = provider.capabilities.minimum_catalog_update_interval_seconds
                if minimum is None or preference.interval_seconds is None:
                    raise CapabilityUnavailable()
                if preference.interval_seconds < minimum:
                    raise CapabilityUnavailable()
            if not isinstance(provider, CatalogUpdateProvider):
                raise CapabilityUnavailable()
            self._enforce_cooldown(previous, started_at, trigger, preference)
            if cancelled():
                raise _CancelledUpdate()
            response = provider.get_chapter_catalog(previous.manga, is_cancelled=cancelled)
            if not isinstance(response, ChapterCatalogResponse) or not response.complete:
                raise ProviderResponseInvalid()
            if cancelled():
                raise _CancelledUpdate()
            if not isinstance(response.chapters, tuple):
                raise ProviderResponseInvalid()
            if any(chapter.manga_id != manga_id for chapter in response.chapters):
                raise ProviderResponseInvalid()
            reconciliation = reconcile_chapters(previous.chapters, response.chapters)
            is_baseline = not self._updates.has_successful_check(manga_id)
            new_source_chapter_ids = () if is_baseline else reconciliation.new_source_chapter_ids
            refreshed_manga = replace(previous.manga, chapters=reconciliation.chapters)
            finished_at = _aware_utc(self._clock())
            snapshot = CatalogSnapshot(
                provider_id=previous.provider_id,
                source_id=previous.source_id,
                manga=refreshed_manga,
                updated_at=finished_at,
                simulated=False,
            )
            check = UpdateCheck(
                manga_id=manga_id,
                provider_id=previous.provider_id,
                started_at=started_at,
                finished_at=finished_at,
                status=UpdateCheckStatus.SUCCEEDED,
                chapter_count=len(snapshot.chapters),
                new_chapter_count=len(new_source_chapter_ids),
                policy_fingerprint=policy_fingerprint,
            )
            notices = self._updates.commit_snapshot(
                snapshot,
                check,
                new_source_chapter_ids,
            )
            return RefreshMangaCatalogResult(snapshot, check, notices)
        except _CancelledUpdate:
            check = UpdateCheck(
                manga_id=manga_id,
                provider_id=previous.provider_id,
                started_at=started_at,
                finished_at=_aware_utc(self._clock()),
                status=UpdateCheckStatus.CANCELLED,
                safe_error_code="UPDATE_CANCELLED",
                policy_fingerprint=policy_fingerprint,
            )
            self._updates.record_check(check)
            raise CatalogRefreshCancelled("A atualização foi cancelada.") from None
        except ProviderError as error:
            status = _status_for_error(error)
            self._record_failure(
                previous,
                started_at,
                status,
                error.code.value,
                retry_after_seconds=getattr(error, "retry_after_seconds", None),
                policy_fingerprint=policy_fingerprint,
            )
            raise
        except (DomainValidationError, TypeError, ValueError, AttributeError):
            self._record_failure(
                previous,
                started_at,
                UpdateCheckStatus.FAILED,
                ProviderErrorCode.PROVIDER_RESPONSE_INVALID.value,
                policy_fingerprint=policy_fingerprint,
            )
            raise ProviderResponseInvalid() from None
        except Exception:
            self._record_failure(
                previous,
                started_at,
                UpdateCheckStatus.FAILED,
                ProviderErrorCode.PROVIDER_UNAVAILABLE.value,
                policy_fingerprint=policy_fingerprint,
            )
            raise ProviderUnavailable() from None

    def _enforce_cooldown(
        self,
        previous: CatalogSnapshot,
        now: datetime,
        trigger: UpdateTrigger,
        preference: UpdatePreference,
    ) -> None:
        provider = self._providers.by_id(previous.provider_id)
        latest = self._updates.latest_check(previous.manga.id)
        latest_provider = self._updates.latest_provider_check(previous.provider_id)
        requests_per_minute = provider.capabilities.requests_per_minute
        if requests_per_minute is not None and latest_provider is not None:
            request_spacing = ceil(60 / requests_per_minute)
            next_provider_request = latest_provider.started_at + timedelta(seconds=request_spacing)
            if now < next_provider_request:
                raise RateLimited(max(1, ceil((next_provider_request - now).total_seconds())))
            if latest_provider.retry_after_at is not None and now < latest_provider.retry_after_at:
                raise RateLimited(
                    max(1, ceil((latest_provider.retry_after_at - now).total_seconds()))
                )
        if latest is None:
            return
        candidate_intervals: list[int] = []
        if trigger is UpdateTrigger.SCHEDULED:
            if preference.interval_seconds is not None:
                candidate_intervals.append(preference.interval_seconds)
            if provider.capabilities.minimum_catalog_update_interval_seconds is not None:
                candidate_intervals.append(
                    provider.capabilities.minimum_catalog_update_interval_seconds
                )
        if candidate_intervals:
            next_allowed = latest.started_at + timedelta(seconds=max(candidate_intervals))
            if now < next_allowed:
                raise RateLimited(max(1, ceil((next_allowed - now).total_seconds())))
        if latest.retry_after_at is not None and now < latest.retry_after_at:
            raise RateLimited(max(1, ceil((latest.retry_after_at - now).total_seconds())))

    def _record_failure(
        self,
        previous: CatalogSnapshot,
        started_at: datetime,
        status: UpdateCheckStatus,
        code: str,
        *,
        retry_after_seconds: int | None = None,
        policy_fingerprint: str | None = None,
    ) -> None:
        finished_at = _aware_utc(self._clock())
        check = UpdateCheck(
            manga_id=previous.manga.id,
            provider_id=previous.provider_id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            safe_error_code=code,
            retry_after_at=(
                finished_at + timedelta(seconds=retry_after_seconds)
                if retry_after_seconds is not None
                else None
            ),
            policy_fingerprint=policy_fingerprint,
        )
        self._updates.record_check(check)


class _CancelledUpdate(Exception):
    pass


def _status_for_error(error: ProviderError) -> UpdateCheckStatus:
    if error.code is ProviderErrorCode.RATE_LIMITED:
        return UpdateCheckStatus.RATE_LIMITED
    if error.code in {
        ProviderErrorCode.CAPABILITY_UNAVAILABLE,
        ProviderErrorCode.UNSUPPORTED_SOURCE,
    }:
        return UpdateCheckStatus.UNSUPPORTED
    return UpdateCheckStatus.FAILED


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("O relógio da aplicação precisa retornar horário com fuso.")
    return value.astimezone(UTC)


def _provider_policy_fingerprint(capabilities: ProviderCapabilities) -> str:
    policy = {
        "provider_id": capabilities.provider_id,
        "allowed_hosts": sorted(capabilities.allowed_hosts),
        "allowed_ports": sorted(capabilities.allowed_ports),
        "allowed_schemes": sorted(capabilities.allowed_schemes),
        "metadata": capabilities.metadata,
        "chapters": capabilities.chapters,
        "simulated": capabilities.simulated,
        "catalog_query_authorized": capabilities.catalog_query_authorized,
        "catalog_query_evidence": capabilities.catalog_query_evidence,
        "catalog_query_reviewed_on": (
            capabilities.catalog_query_reviewed_on.isoformat()
            if capabilities.catalog_query_reviewed_on is not None
            else None
        ),
        "catalog_query_scope": capabilities.catalog_query_scope,
        "requests_per_minute": capabilities.requests_per_minute,
        "periodic_catalog_updates_authorized": (
            capabilities.periodic_catalog_updates_authorized
        ),
        "minimum_catalog_update_interval_seconds": (
            capabilities.minimum_catalog_update_interval_seconds
        ),
    }
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
