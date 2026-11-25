from __future__ import annotations

import pytest

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.providers import RedirectRejected, UnsafeDestination
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


def test_declared_host_does_not_allow_suffix_or_private_dns_rebinding() -> None:
    policy = ExternalUrlPolicy(lambda _host: ["8.8.8.8"])
    with pytest.raises(UnsafeDestination):
        policy.validate(
            normalize_url("https://manga.example.test.attacker.invalid/page"),
            allowed_hosts=frozenset({"example.test"}),
        )

    answers = iter([["8.8.8.8"], ["127.0.0.1"]])
    changing = ExternalUrlPolicy(lambda _host: next(answers))
    start = normalize_url("https://manga.example.test/start")
    destination = changing.validate(start, allowed_hosts=frozenset({start.host}))
    with pytest.raises(UnsafeDestination):
        destination.assert_connected_address("127.0.0.1")


def test_redirect_to_undeclared_or_private_destination_is_rejected() -> None:
    policy = ExternalUrlPolicy(
        lambda host: ["10.0.0.9"] if host == "private.example.test" else ["8.8.8.8"]
    )
    start = normalize_url("https://manga.example.test/start")

    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["https://cdn.example.test/page"],
            allowed_hosts=frozenset({"manga.example.test"}),
        )
    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["https://private.example.test/page"],
            allowed_hosts=frozenset({"manga.example.test", "private.example.test"}),
        )
