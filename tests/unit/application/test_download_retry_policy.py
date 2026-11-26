from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from manga_to_kindle.application.downloads.retry_policy import decide_retry


def test_retry_policy_uses_bounded_backoff_for_transient_failures() -> None:
    now = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)

    first = decide_retry(attempts_made=1, now=now, status_code=503)
    third = decide_retry(attempts_made=3, now=now, retryable_transport_error=True)
    exhausted = decide_retry(attempts_made=4, now=now, status_code=503)
    blocked = decide_retry(attempts_made=1, now=now, status_code=403)

    assert first.delay_seconds == 1
    assert third.delay_seconds == 4
    assert not exhausted.retry
    assert not blocked.retry


def test_retry_after_seconds_and_http_date_are_minimum_deadlines() -> None:
    now = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    future = now + timedelta(minutes=2)
    seconds = decide_retry(
        attempts_made=1,
        now=now,
        status_code=429,
        headers={"Retry-After": "120"},
    )
    date_header = decide_retry(
        attempts_made=1,
        now=now,
        status_code=503,
        headers={"retry-after": format_datetime(future, usegmt=True)},
    )

    assert seconds.next_attempt_at == future
    assert date_header.next_attempt_at == future
    assert seconds.delay_seconds == 120


def test_expired_or_malformed_retry_after_falls_back_to_backoff() -> None:
    now = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)

    expired = decide_retry(
        attempts_made=1,
        now=now,
        status_code=429,
        headers={"Retry-After": "0"},
    )
    malformed = decide_retry(
        attempts_made=1,
        now=now,
        status_code=429,
        headers={"Retry-After": "later"},
    )

    assert expired.delay_seconds == 1
    assert malformed.delay_seconds == 1
