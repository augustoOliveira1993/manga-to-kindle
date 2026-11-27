from __future__ import annotations

import json

from manga_to_kindle.application.catalog.get_catalog import GetCatalog
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.providers.ndl_provider import NdlProvider


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}
    connected_address = "93.184.216.34"

    def __init__(self, payload: object) -> None:
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

    def get(self, _url, **_kwargs) -> FakeResponse:
        return self.response


def test_ndl_catalog_flows_through_registry_without_fixture_fallback() -> None:
    response = FakeResponse(
        {
            "id": "851650",
            "title": "北斎漫画",
            "volume": "５編",
            "responsibility": "葛飾北斎",
            "page": 33,
        }
    )
    provider = NdlProvider(
        FakeTransport(response),
        ExternalUrlPolicy(lambda _host: ("93.184.216.34",)),
    )
    snapshot = GetCatalog(ProviderRegistry((provider,))).execute(
        "https://lab.ndl.go.jp/dl/book/851650"
    )

    assert snapshot.provider_id == "ndl-next-digital-library"
    assert snapshot.source_id == "ndl:851650"
    assert snapshot.manga.title == "北斎漫画"
    assert snapshot.simulated is False
    assert len(snapshot.chapters) == 1
    assert response.closed
