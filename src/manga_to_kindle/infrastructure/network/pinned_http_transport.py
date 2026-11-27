"""HTTPS transport that connects only to an address already approved by URL policy."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Iterable, Mapping
from typing import Protocol

from manga_to_kindle.domain.providers import NormalizedUrl, ProviderError, ProviderPageReference
from manga_to_kindle.infrastructure.downloads.transport import (
    CancellationSignal,
    DownloadResponse,
    DownloadTransport,
    TransportFailure,
)
from manga_to_kindle.infrastructure.network.url_policy import (
    ExternalUrlPolicy,
    ValidatedDestination,
)

CHUNK_SIZE = 64 * 1024
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


class CancellationProbe(Protocol):
    @property
    def cancelled(self) -> bool: ...


class PinnedHttpResponse:
    def __init__(
        self,
        connection: _PinnedHTTPSConnection,
        response: http.client.HTTPResponse,
        connected_address: str,
        validated_destination: ValidatedDestination,
        cancellation: CancellationProbe,
    ) -> None:
        self._connection = connection
        self._response = response
        self._cancellation = cancellation
        self.status_code = response.status
        self.headers: Mapping[str, str] = dict(response.getheaders())
        self.connected_address = connected_address
        self.validated_destination = validated_destination

    def iter_chunks(self) -> Iterable[bytes]:
        while True:
            chunk = self._response.read(CHUNK_SIZE)
            if not chunk:
                return
            yield chunk
            if self._cancellation.cancelled:
                return

    def read_limited(self, maximum_bytes: int) -> bytes:
        if maximum_bytes < 1:
            raise ValueError("O limite de resposta precisa ser positivo.")
        body = bytearray()
        for chunk in self.iter_chunks():
            body.extend(chunk)
            if len(body) > maximum_bytes:
                raise TransportFailure("RESPONSE_TOO_LARGE", retryable=False)
        return bytes(body)

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self._connection.close()


class PinnedHttpTransport(DownloadTransport):
    """Performs pinned HTTPS GETs and validates every allowed redirect hop."""

    def __init__(
        self,
        url_policy: ExternalUrlPolicy,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        self._url_policy = url_policy
        self._tls_context = tls_context or ssl.create_default_context()

    def open(
        self,
        reference: ProviderPageReference,
        *,
        destination: ValidatedDestination,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        cancellation: CancellationSignal,
    ) -> DownloadResponse:
        response = self.get(
            reference.destination,
            destination=destination,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
            cancellation=cancellation,
        )
        content_type = _header(response.headers, "content-type")
        if (
            reference.destination.path.lower().endswith((".jpg", ".jpeg"))
            and content_type is not None
            and content_type.strip().lower() in {"application/octet-stream", "binary/octet-stream"}
        ):
            response.headers = {**response.headers, "Content-Type": "image/jpeg"}
        return response

    def get(
        self,
        url: NormalizedUrl,
        *,
        destination: ValidatedDestination,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        cancellation: CancellationProbe,
    ) -> PinnedHttpResponse:
        current_url = url
        current_destination = destination
        locations: list[str] = []
        for redirect_count in range(_MAX_REDIRECTS + 1):
            response = self._get_once(
                current_url,
                current_destination,
                connect_timeout_seconds=connect_timeout_seconds,
                read_timeout_seconds=read_timeout_seconds,
                cancellation=cancellation,
            )
            if response.status_code not in _REDIRECT_STATUSES:
                return response
            location = _header(response.headers, "location")
            if not location:
                return response
            if redirect_count == _MAX_REDIRECTS:
                response.close()
                raise TransportFailure("REDIRECT_REJECTED", retryable=False)
            response.close()
            locations.append(location)
            try:
                chain = self._url_policy.validate_redirect_chain(
                    url,
                    locations,
                    allowed_hosts=destination.allowed_hosts,
                    allowed_ports=destination.allowed_ports,
                    allowed_schemes=destination.allowed_schemes,
                    max_redirects=_MAX_REDIRECTS,
                )
                current_url = chain[-1]
                current_destination = self._url_policy.validate(
                    current_url,
                    allowed_hosts=destination.allowed_hosts,
                    allowed_ports=destination.allowed_ports,
                    allowed_schemes=destination.allowed_schemes,
                )
            except ProviderError:
                raise TransportFailure("REDIRECT_REJECTED", retryable=False) from None
        raise TransportFailure("REDIRECT_REJECTED", retryable=False)

    def _get_once(
        self,
        url: NormalizedUrl,
        destination: ValidatedDestination,
        *,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        cancellation: CancellationProbe,
    ) -> PinnedHttpResponse:
        if url.scheme != "https" or destination.scheme != "https":
            raise TransportFailure("HTTPS_REQUIRED", retryable=False)
        if url.host != destination.hostname or url.port != destination.port:
            raise TransportFailure("DESTINATION_MISMATCH", retryable=False)
        if cancellation.cancelled:
            raise TransportFailure("REQUEST_CANCELLED", retryable=False)

        connection = _PinnedHTTPSConnection(
            url.host,
            url.port,
            destination,
            self._tls_context,
            connect_timeout_seconds,
            read_timeout_seconds,
        )
        try:
            target = url.path + (f"?{url.query}" if url.query else "")
            if "\r" in target or "\n" in target:
                raise TransportFailure("INVALID_REQUEST_TARGET", retryable=False)
            connection.request(
                "GET",
                target,
                headers={
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                    "Host": _host_header(url),
                    "User-Agent": "MangaToKindle/0.1",
                },
            )
            response = connection.getresponse()
            if connection.connected_address is None:
                raise TransportFailure("CONNECTION_ADDRESS_UNAVAILABLE", retryable=False)
            destination.assert_connected_address(connection.connected_address)
            return PinnedHttpResponse(
                connection,
                response,
                connection.connected_address,
                destination,
                cancellation,
            )
        except TransportFailure:
            connection.close()
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException, TimeoutError):
            connection.close()
            raise TransportFailure("HTTPS_REQUEST_FAILED") from None
        except Exception:
            connection.close()
            raise


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        destination: ValidatedDestination,
        tls_context: ssl.SSLContext,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
    ) -> None:
        super().__init__(host, port, timeout=connect_timeout_seconds, context=tls_context)
        self._destination = destination
        self._tls_context = tls_context
        self._read_timeout_seconds = read_timeout_seconds
        self.connected_address: str | None = None

    def connect(self) -> None:
        last_error: OSError | None = None
        for approved_address in sorted(self._destination.approved_addresses):
            address = ipaddress.ip_address(approved_address)
            family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
            raw_socket = socket.socket(family, socket.SOCK_STREAM)
            raw_socket.settimeout(self.timeout)
            secure_socket: ssl.SSLSocket | None = None
            try:
                sockaddr: tuple[object, ...]
                if address.version == 6:
                    sockaddr = (approved_address, self.port, 0, 0)
                else:
                    sockaddr = (approved_address, self.port)
                raw_socket.connect(sockaddr)
                secure_socket = self._tls_context.wrap_socket(
                    raw_socket,
                    server_hostname=self._destination.hostname,
                )
                secure_socket.settimeout(self._read_timeout_seconds)
                self._destination.assert_connected_address(secure_socket.getpeername()[0])
                self.sock = secure_socket
                self.connected_address = secure_socket.getpeername()[0]
                return
            except Exception as error:
                if secure_socket is not None:
                    secure_socket.close()
                else:
                    raw_socket.close()
                if isinstance(error, OSError):
                    last_error = error
                    continue
                raise
        if last_error is None:
            raise OSError("No approved connection address")
        raise last_error


def _host_header(url: NormalizedUrl) -> str:
    return url.authority


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return next((value for key, value in headers.items() if key.lower() == name), None)
