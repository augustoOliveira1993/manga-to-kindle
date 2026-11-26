from __future__ import annotations

from tests.download_support import FakeTransport, NeverCancelled, make_reference

from manga_to_kindle.application.downloads.queue import (
    CONNECT_TIMEOUT_SECONDS,
    READ_TIMEOUT_SECONDS,
)
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


def test_isolated_transport_contract_carries_pinned_destination_and_timeouts() -> None:
    reference = make_reference("transport-page", 0)
    destination = ExternalUrlPolicy(lambda _host: ("93.184.216.34",)).validate(
        reference.destination,
        allowed_hosts=frozenset({"pages.example.test"}),
        allowed_ports=frozenset({443}),
        allowed_schemes=frozenset({"https"}),
    )
    transport = FakeTransport()

    response = transport.open(
        reference,
        destination=destination,
        connect_timeout_seconds=CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds=READ_TIMEOUT_SECONDS,
        cancellation=NeverCancelled(),
    )
    try:
        assert response.status_code == 200
        assert response.connected_address in destination.approved_addresses
        assert b"".join(response.iter_chunks())
        assert transport.destinations == [destination]
        assert transport.calls == [
            (reference, CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
        ]
    finally:
        response.close()
    assert transport.active == 0
