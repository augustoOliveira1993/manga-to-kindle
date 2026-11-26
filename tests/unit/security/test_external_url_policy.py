from __future__ import annotations

import pytest

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.application.providers.resolve_provider import resolve_provider
from manga_to_kindle.domain.providers import InvalidUrl, RedirectRejected, UnsafeDestination
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.providers.fixture_provider import FixtureProvider


def test_normalization_canonicalizes_host_port_and_fragment_but_preserves_query() -> None:
    url = normalize_url(" HTTPS://Münich.Example:443/a%2Fb?token=private#page ")

    assert url.scheme == "https"
    assert url.host == "xn--mnich-kva.example"
    assert url.port == 443
    assert url.path == "/a%2Fb"
    assert url.query == "token=private"
    assert "private" not in repr(url)
    assert url.render() == "https://xn--mnich-kva.example/a%2Fb?token=private"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://example.test/book",
        "https://user:secret@example.test/book",
        "https://example.test:70000/book",
        "https://example.test:/book",
        "https://example.test/a b",
        "//example.test/book",
    ],
)
def test_invalid_external_urls_fail_before_resolution(value: str) -> None:
    with pytest.raises(InvalidUrl):
        resolve_provider(value, ProviderRegistry([FixtureProvider()]))


@pytest.mark.parametrize("address", ["127.0.0.1", "10.1.2.3", "169.254.169.254", "::1"])
def test_private_ip_literals_are_rejected(address: str) -> None:
    scheme = "http" if ":" not in address else "http"
    host = f"[{address}]" if ":" in address else address
    policy = ExternalUrlPolicy(lambda _host: pytest.fail("literal IP must not resolve"))

    with pytest.raises(UnsafeDestination):
        policy.validate(
            normalize_url(f"{scheme}://{host}/"),
            allowed_hosts=frozenset({address}),
            allowed_ports=frozenset({80}),
            allowed_schemes=frozenset({"http"}),
        )


def test_dns_mixed_answers_fail_closed_and_connected_ip_must_match() -> None:
    mixed = ExternalUrlPolicy(lambda _host: ["8.8.8.8", "10.0.0.4"])
    url = normalize_url("https://manga.example.test/chapters")
    with pytest.raises(UnsafeDestination):
        mixed.validate(url, allowed_hosts=frozenset({url.host}))

    public = ExternalUrlPolicy(lambda _host: ["8.8.8.8"])
    target = public.validate(url, allowed_hosts=frozenset({url.host}))
    target.assert_connected_address("8.8.8.8")
    with pytest.raises(UnsafeDestination):
        target.assert_connected_address("127.0.0.1")


def test_redirect_chain_revalidates_host_scheme_loop_and_hop_limit() -> None:
    policy = ExternalUrlPolicy(
        lambda host: ["8.8.8.8"] if host.endswith("example.test") else ["10.0.0.2"]
    )
    start = normalize_url("https://manga.example.test/start")
    allowed = frozenset({"manga.example.test", "cdn.example.test"})

    chain = policy.validate_redirect_chain(
        start,
        ["https://cdn.example.test/image/1"],
        allowed_hosts=allowed,
    )
    assert len(chain) == 2

    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["http://manga.example.test/downgrade"],
            allowed_hosts=allowed,
        )
    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["/start"],
            allowed_hosts=allowed,
        )
    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["/1", "/2", "/3", "/4", "/5", "/6"],
            allowed_hosts=allowed,
        )


def test_scheme_capability_is_checked_for_initial_and_redirect_destinations() -> None:
    policy = ExternalUrlPolicy(lambda _host: ["8.8.8.8"])
    start = normalize_url("http://manga.example.test/start")
    allowed = frozenset({"manga.example.test"})

    with pytest.raises(UnsafeDestination):
        policy.validate(
            start,
            allowed_hosts=allowed,
            allowed_schemes=frozenset({"https"}),
        )

    validated = policy.validate(
        start,
        allowed_hosts=allowed,
        allowed_ports=frozenset({80}),
        allowed_schemes=frozenset({"http"}),
    )
    assert validated.scheme == "http"

    with pytest.raises(RedirectRejected):
        policy.validate_redirect_chain(
            start,
            ["http://manga.example.test/next"],
            allowed_hosts=allowed,
            allowed_ports=frozenset({80}),
            allowed_schemes=frozenset({"https"}),
        )
