from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.updates.scheduler import PeriodicUpdateScheduler
from manga_to_kindle.domain.providers import ProviderCapabilities
from manga_to_kindle.domain.updates import (
    UpdateCheck,
    UpdateCheckStatus,
    UpdateMangaStatus,
    UpdatePreference,
)

FAKE_CLOCK = Path(__file__).parents[2] / "fixtures" / "updates" / "fake_clock.json"


class SchedulerProvider:
    provider_id = "authorized-metadata"
    capabilities = ProviderCapabilities(
        provider_id=provider_id,
        allowed_hosts=frozenset({"updates.example"}),
        metadata=True,
        chapters=True,
        requests_per_minute=1,
        catalog_query_authorized=True,
        catalog_query_evidence="review:terms-v1",
        catalog_query_reviewed_on=date(2026, 1, 1),
        catalog_query_scope="chapter metadata",
        periodic_catalog_updates_authorized=True,
        minimum_catalog_update_interval_seconds=60,
    )


def item(
    *,
    enabled: bool = True,
    simulated: bool = False,
    interval_seconds: int = 120,
    updated_at: datetime | None = None,
    last_check: UpdateCheck | None = None,
    provider_id: str | None = SchedulerProvider.provider_id,
) -> UpdateMangaStatus:
    manga_id = uuid4()
    if last_check is not None:
        last_check = UpdateCheck(
            manga_id=manga_id,
            provider_id=last_check.provider_id,
            started_at=last_check.started_at,
            finished_at=last_check.finished_at,
            status=last_check.status,
            chapter_count=last_check.chapter_count,
            new_chapter_count=last_check.new_chapter_count,
            safe_error_code=last_check.safe_error_code,
            retry_after_at=last_check.retry_after_at,
        )
    return UpdateMangaStatus(
        manga_id=manga_id,
        title="Manga local",
        provider_id=provider_id,
        simulated=simulated,
        chapter_count=1,
        preference=UpdatePreference(
            manga_id=manga_id,
            enabled=enabled,
            interval_seconds=interval_seconds if enabled else None,
            updated_at=updated_at,
        ),
        last_check=last_check,
    )


def test_scheduler_is_off_by_default_and_ignores_simulated_or_unsupported_items() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    providers = ProviderRegistry((SchedulerProvider(),))
    scheduler = PeriodicUpdateScheduler()
    statuses = (
        item(enabled=False, updated_at=now - timedelta(days=1)),
        item(simulated=True, updated_at=now - timedelta(days=1)),
        item(provider_id="not-registered", updated_at=now - timedelta(days=1)),
    )

    assert scheduler.claim_due(statuses, providers, now) is None


def test_scheduler_waits_for_opt_in_interval_then_coalesces_due_work() -> None:
    clock = json.loads(FAKE_CLOCK.read_text(encoding="utf-8"))
    baseline = datetime.fromisoformat(clock["baseline"])
    due = datetime.fromisoformat(clock["after_minimum_interval"])
    provider = SchedulerProvider()
    providers = ProviderRegistry((provider,))
    first = item(interval_seconds=60, updated_at=baseline)
    second = item(updated_at=baseline - timedelta(seconds=1000))
    scheduler = PeriodicUpdateScheduler()

    assert scheduler.claim_due((first,), providers, due - timedelta(seconds=1)) is None
    scheduled = scheduler.claim_due((first, second), providers, due)
    assert scheduled is not None
    assert scheduled.manga_id == second.manga_id
    assert scheduler.claim_due((first, second), providers, due) is None
    scheduler.release(scheduled)


def test_scheduler_respects_policy_minimum_and_retry_after() -> None:
    clock = json.loads(FAKE_CLOCK.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(clock["baseline"])
    retry_at = datetime.fromisoformat(clock["after_retry_after"])
    manga = item(
        updated_at=now - timedelta(days=1),
        interval_seconds=300,
        last_check=UpdateCheck(
            manga_id=uuid4(),
            provider_id=SchedulerProvider.provider_id,
            started_at=now - timedelta(days=1),
            finished_at=now - timedelta(days=1),
            status=UpdateCheckStatus.RATE_LIMITED,
            safe_error_code="RATE_LIMITED",
            retry_after_at=retry_at,
        ),
    )
    scheduler = PeriodicUpdateScheduler()
    providers = ProviderRegistry((SchedulerProvider(),))
    assert scheduler.claim_due((manga,), providers, now) is None
    assert scheduler.claim_due((manga,), providers, retry_at - timedelta(seconds=1)) is None
    assert scheduler.claim_due((manga,), providers, retry_at) is not None


def test_scheduler_applies_provider_rate_limit_across_all_manga() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = item(updated_at=now - timedelta(days=1))
    second = item(updated_at=now - timedelta(days=1))
    first = replace(
        first,
        last_check=UpdateCheck(
            manga_id=first.manga_id,
            provider_id=SchedulerProvider.provider_id,
            started_at=now - timedelta(seconds=30),
            finished_at=now - timedelta(seconds=30),
            status=UpdateCheckStatus.SUCCEEDED,
            chapter_count=1,
        ),
    )
    scheduler = PeriodicUpdateScheduler()
    providers = ProviderRegistry((SchedulerProvider(),))

    assert scheduler.claim_due((first, second), providers, now) is None
    scheduled = scheduler.claim_due(
        (first, second),
        providers,
        now + timedelta(seconds=30),
    )
    assert scheduled is not None
    assert scheduled.manga_id == second.manga_id


def test_scheduler_does_not_schedule_again_after_per_manga_opt_out() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    provider = SchedulerProvider()
    providers = ProviderRegistry((provider,))
    manga = item(updated_at=now - timedelta(days=1))
    scheduler = PeriodicUpdateScheduler()

    scheduled = scheduler.claim_due((manga,), providers, now)
    assert scheduled is not None
    scheduler.release(scheduled)
    opted_out = replace(
        manga,
        preference=UpdatePreference(
            manga_id=manga.manga_id,
            interval_seconds=120,
            notifications_enabled=True,
        ),
    )
    assert scheduler.claim_due((opted_out,), providers, now + timedelta(days=1)) is None
