from __future__ import annotations

from datetime import date

import pytest

from manga_to_kindle.domain.providers import (
    MangaProvider,
    ProviderCapabilities,
    ProviderPageReference,
    RateLimited,
)


def test_download_capability_requires_reviewed_scope_evidence() -> None:
    with pytest.raises(ValueError):
        ProviderCapabilities(
            provider_id="unreviewed",
            allowed_hosts=frozenset({"example.test"}),
            download_authorized=True,
        )

    capability = ProviderCapabilities(
        provider_id="reviewed",
        allowed_hosts=frozenset({"example.test"}),
        download_authorized=True,
        authorization_evidence="https://example.test/terms",
        authorization_reviewed_on=date(2026, 11, 25),
        authorization_scope="Permissão explícita de download local",
    )
    assert capability.download_enabled


def test_rate_limit_error_keeps_only_typed_retry_metadata() -> None:
    error = RateLimited(retry_after_seconds=30)

    assert error.code == "RATE_LIMITED"
    assert error.retryable
    assert error.retry_after_seconds == 30
    assert "token" not in str(error).lower()


def test_provider_protocol_has_explicit_operations() -> None:
    assert {"supports", "get_manga", "get_chapters", "get_pages"}.issubset(
        MangaProvider.__dict__
    )
    assert ProviderPageReference.__dataclass_fields__["source_reference"]
