from __future__ import annotations

import json

import pytest

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.providers import ProviderResponseInvalid, RateLimited, RedirectRejected
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.providers.ndl_provider import NdlProvider


class FakeResponse:
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json; charset=utf-8"}
        self.connected_address = "93.184.216.34"
        self._body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.closed = False

    def read_limited(self, maximum_bytes: int) -> bytes:
        assert len(self._body) <= maximum_bytes
        return self._body

    def close(self) -> None:
        self.closed = True


class FakeTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[object, ...]] = []

    def get(self, url, **kwargs) -> FakeResponse:
        self.calls.append((url, kwargs["destination"], kwargs["connect_timeout_seconds"]))
        return self.response


def _provider(payload: object, *, monotonic=lambda: 120.0):
    response = FakeResponse(payload)
    transport = FakeTransport(response)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    provider = NdlProvider(transport, policy, monotonic=monotonic)
    return provider, transport, response


def _record() -> dict[str, object]:
    return {
        "id": "851650",
        "title": "北斎漫画",
        "volume": "５編",
        "responsibility": "葛飾北斎",
        "published": "明治11 [1878]",
        "page": 33,
        "leftopen": True,
    }


def test_ndl_returns_one_item_and_stable_iiif_page_references() -> None:
    provider, transport, response = _provider(_record())
    url = normalize_url("https://lab.ndl.go.jp/dl/book/851650")

    assert provider.supports(url)
    manga = provider.get_manga(url)
    chapters = provider.get_chapters(manga)
    pages = provider.get_pages(chapters[0])

    assert manga.title == "北斎漫画"
    assert manga.author == "葛飾北斎"
    assert manga.language == "ja"
    assert manga.source_ref == "ndl:851650"
    assert len(chapters) == 1
    assert chapters[0].title == "５編"
    assert len(pages) == 33
    assert pages[0].position == 0
    assert pages[0].source_id == "ndl:851650:1"
    assert pages[0].destination.host == "dl.ndl.go.jp"
    assert pages[0].destination.path == "/api/iiif/851650/R0000001/full/full/0/default.jpg"
    assert transport.calls[0][0].path == "/dl/api/book/851650"
    assert response.closed
    assert provider.capabilities.download_enabled
    assert provider.capabilities.catalog_query_enabled
    assert not provider.capabilities.periodic_catalog_updates_enabled
    assert provider.restore_page_reference("ndl:851650", "ndl:851650:2", 1) == pages[1]


@pytest.mark.parametrize(
    "value",
    (
        "https://lab.ndl.go.jp/dl/book/851650?token=secret",
        "https://dl.ndl.go.jp/dl/book/851650",
        "https://lab.ndl.go.jp/dl/book/not-a-number",
        "http://lab.ndl.go.jp/dl/book/851650",
    ),
)
def test_ndl_supports_only_https_individual_item_page_without_query(value: str) -> None:
    provider, _transport, _response = _provider(_record())
    assert not provider.supports(normalize_url(value))


def test_ndl_rejects_mismatched_item_id_without_saving_catalog() -> None:
    payload = _record()
    payload["id"] = "851651"
    provider, _transport, _response = _provider(payload)

    with pytest.raises(ProviderResponseInvalid):
        provider.get_manga(normalize_url("https://lab.ndl.go.jp/dl/book/851650"))


def test_ndl_applies_local_metadata_rate_limit() -> None:
    ticks = iter((10.0, 20.0))
    provider, transport, _response = _provider(_record(), monotonic=lambda: next(ticks))
    url = normalize_url("https://lab.ndl.go.jp/dl/book/851650")
    provider.get_manga(url)

    with pytest.raises(RateLimited) as error:
        provider.get_manga(url)

    assert error.value.retry_after_seconds == 50
    assert len(transport.calls) == 1


def test_ndl_maps_redirect_to_typed_error_without_following_it() -> None:
    response = FakeResponse(_record(), status_code=302)
    provider = NdlProvider(
        FakeTransport(response),
        ExternalUrlPolicy(lambda _host: ("93.184.216.34",)),
    )

    with pytest.raises(RedirectRejected):
        provider.get_manga(normalize_url("https://lab.ndl.go.jp/dl/book/851650"))

    assert response.closed
