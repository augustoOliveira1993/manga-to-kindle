"""Política pura e determinística de tentativas e Retry-After."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

MAX_ADDITIONAL_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = (1, 2, 4)
MAX_BACKOFF_SECONDS = 60


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    next_attempt_at: datetime | None
    delay_seconds: float | None


def decide_retry(
    *,
    attempts_made: int,
    now: datetime,
    status_code: int | None = None,
    retryable_transport_error: bool = False,
    headers: Mapping[str, str] | None = None,
) -> RetryDecision:
    """Retorna prazo mínimo sem reduzir Retry-After para caber no backoff local."""
    if now.utcoffset() is None:
        raise ValueError("O relógio de retry precisa conter fuso horário.")
    eligible = retryable_transport_error or status_code in {408, 429} or (
        status_code is not None and 500 <= status_code <= 599
    )
    if not eligible or attempts_made < 1 or attempts_made > MAX_ADDITIONAL_ATTEMPTS:
        return RetryDecision(False, None, None)

    backoff = min(
        DEFAULT_BACKOFF_SECONDS[min(attempts_made - 1, len(DEFAULT_BACKOFF_SECONDS) - 1)],
        MAX_BACKOFF_SECONDS,
    )
    deadline = now.astimezone(UTC) + timedelta(seconds=backoff)
    retry_after = _retry_after_deadline(headers or {}, now.astimezone(UTC))
    if retry_after is not None:
        deadline = max(deadline, retry_after)
    delay = max(0.0, (deadline - now.astimezone(UTC)).total_seconds())
    return RetryDecision(True, deadline, delay)


def _retry_after_deadline(
    headers: Mapping[str, str], now: datetime
) -> datetime | None:
    value = next(
        (value.strip() for key, value in headers.items() if key.lower() == "retry-after"),
        None,
    )
    if not value:
        return None
    try:
        seconds = int(value, 10)
    except ValueError:
        try:
            deadline = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if deadline.tzinfo is None:
            return None
        deadline = deadline.astimezone(UTC)
        return deadline if deadline > now else None
    if seconds < 0:
        return None
    try:
        deadline = now + timedelta(seconds=seconds)
    except OverflowError:
        return datetime.max.replace(tzinfo=UTC)
    return deadline if deadline > now else None
