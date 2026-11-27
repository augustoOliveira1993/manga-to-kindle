from __future__ import annotations

import socket

import pytest

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.providers import ProviderPageReference
from manga_to_kindle.infrastructure.downloads.transport import TransportFailure
from manga_to_kindle.infrastructure.network import pinned_http_transport
from manga_to_kindle.infrastructure.network.pinned_http_transport import (
    PinnedHttpTransport,
    _PinnedHTTPSConnection,
)
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


class FakeSocket:
    def __init__(self, family: int) -> None:
        self.family = family
        self.address = None
        self.closed = False

    def settimeout(self, _seconds: float | None) -> None:
        return None

    def connect(self, address: tuple[object, ...]) -> None:
        self.address = address

    def close(self) -> None:
        self.closed = True


class FakeSecureSocket:
    def __init__(self, raw_socket: FakeSocket) -> None:
        self.raw_socket = raw_socket
        self.read_timeout = None

    def settimeout(self, seconds: float) -> None:
        self.read_timeout = seconds

    def getpeername(self) -> tuple[str, int]:
        assert self.raw_socket.address is not None
        return str(self.raw_socket.address[0]), 443

    def close(self) -> None:
        self.raw_socket.close()


class FakeTlsContext:
    def __init__(self) -> None:
        self.server_names: list[str] = []

    def wrap_socket(self, raw_socket: FakeSocket, *, server_hostname: str) -> FakeSecureSocket:
        self.server_names.append(server_hostname)
        return FakeSecureSocket(raw_socket)


class FakeHttpResponse:
    def __init__(self, status: int, headers: dict[str, str]) -> None:
        self.status = status
        self.headers = headers
        self.closed = False

    def getheaders(self) -> list[tuple[str, str]]:
        return list(self.headers.items())

    def read(self, _size: int = -1) -> bytes:
        return b""

    def close(self) -> None:
        self.closed = True


class FakePinnedConnection:
    responses: list[FakeHttpResponse] = []
    requests: list[tuple[str, str, dict[str, str]]] = []

    def __init__(self, host: str, *_args) -> None:
        self.host = host
        self.connected_address = {
            "dl.ndl.go.jp": "93.184.216.34",
            "dss-r4-prod-contents-download.s3.amazonaws.com": "1.1.1.1",
        }[host]

    def request(self, method: str, target: str, *, headers: dict[str, str]) -> None:
        self.requests.append((self.host, target, headers))

    def getresponse(self) -> FakeHttpResponse:
        return self.responses.pop(0)

    def close(self) -> None:
        return None


def test_connection_uses_only_validated_ip_and_keeps_tls_host(monkeypatch) -> None:
    raw_sockets: list[FakeSocket] = []
    context = FakeTlsContext()

    def make_socket(family: int, _kind: int) -> FakeSocket:
        raw = FakeSocket(family)
        raw_sockets.append(raw)
        return raw

    def reject_dns(*_args, **_kwargs):
        raise AssertionError("the transport must not resolve DNS again")

    monkeypatch.setattr(socket, "socket", make_socket)
    monkeypatch.setattr(socket, "getaddrinfo", reject_dns)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34", "1.1.1.1"))
    url = normalize_url("https://pages.example.test/image/1.jpg")
    destination = policy.validate(
        url,
        allowed_hosts=frozenset({"pages.example.test"}),
        allowed_ports=frozenset({443}),
        allowed_schemes=frozenset({"https"}),
    )
    connection = _PinnedHTTPSConnection(
        url.host,
        url.port,
        destination,
        context,
        connect_timeout_seconds=4.0,
        read_timeout_seconds=9.0,
    )

    connection.connect()

    assert len(raw_sockets) == 1
    assert raw_sockets[0].address in {
        (address, 443) for address in destination.approved_addresses
    }
    assert context.server_names == ["pages.example.test"]
    assert connection.connected_address in destination.approved_addresses
    assert connection.sock.read_timeout == 9.0
    connection.close()


def test_pinned_transport_revalidates_ndl_image_redirect_before_following(monkeypatch) -> None:
    delivery_host = "dss-r4-prod-contents-download.s3.amazonaws.com"
    policy = ExternalUrlPolicy(
        lambda host: {
            "dl.ndl.go.jp": ("93.184.216.34",),
            delivery_host: ("1.1.1.1",),
        }[host]
    )
    url = normalize_url("https://dl.ndl.go.jp/api/iiif/851650/R0000021/full/full/0/default.jpg")
    allowed_hosts = frozenset({"dl.ndl.go.jp", delivery_host})
    destination = policy.validate(url, allowed_hosts=allowed_hosts)
    reference = ProviderPageReference(
        source_id="ndl:851650:21",
        position=20,
        source_reference="ndl:851650:21",
        destination=url,
    )
    FakePinnedConnection.responses = [
        FakeHttpResponse(
            307,
            {"Location": f"https://{delivery_host}/object.jpg?signature=secret"},
        ),
        FakeHttpResponse(200, {"Content-Type": "binary/octet-stream"}),
    ]
    FakePinnedConnection.requests = []
    monkeypatch.setattr(
        pinned_http_transport,
        "_PinnedHTTPSConnection",
        FakePinnedConnection,
    )

    response = PinnedHttpTransport(policy).open(
        reference,
        destination=destination,
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        cancellation=type("NotCancelled", (), {"cancelled": False})(),
    )

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/jpeg"
    assert [request[0] for request in FakePinnedConnection.requests] == [
        "dl.ndl.go.jp",
        delivery_host,
    ]
    assert FakePinnedConnection.requests[1][1].endswith("signature=secret")
    assert response.validated_destination.hostname == delivery_host
    response.close()


def test_pinned_transport_rejects_unapproved_redirect_without_following(monkeypatch) -> None:
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    url = normalize_url("https://dl.ndl.go.jp/api/iiif/851650/R0000021/full/full/0/default.jpg")
    destination = policy.validate(url, allowed_hosts=frozenset({"dl.ndl.go.jp"}))
    reference = ProviderPageReference(
        source_id="ndl:851650:21",
        position=20,
        source_reference="ndl:851650:21",
        destination=url,
    )
    FakePinnedConnection.responses = [
        FakeHttpResponse(307, {"Location": "https://evil.example.test/object.jpg"})
    ]
    FakePinnedConnection.requests = []
    monkeypatch.setattr(
        pinned_http_transport,
        "_PinnedHTTPSConnection",
        FakePinnedConnection,
    )

    with pytest.raises(TransportFailure, match="^REDIRECT_REJECTED$"):
        PinnedHttpTransport(policy).open(
            reference,
            destination=destination,
            connect_timeout_seconds=1,
            read_timeout_seconds=1,
            cancellation=type("NotCancelled", (), {"cancelled": False})(),
        )

    assert len(FakePinnedConnection.requests) == 1
