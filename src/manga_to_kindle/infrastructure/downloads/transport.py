"""Contrato de transporte em fluxo; esta camada não habilita tráfego de rede."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from manga_to_kindle.domain.providers import ProviderPageReference
from manga_to_kindle.infrastructure.network.url_policy import ValidatedDestination


class CancellationSignal(Protocol):
    @property
    def cancelled(self) -> bool: ...

    def wait(self, timeout_seconds: float) -> bool: ...


class DownloadResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    connected_address: str

    def iter_chunks(self) -> Iterable[bytes]: ...

    def close(self) -> None: ...


class DownloadTransport(Protocol):
    """Transporte em fluxo sem redirect automático ou descompressão do conteúdo."""

    def open(
        self,
        reference: ProviderPageReference,
        *,
        destination: ValidatedDestination,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        cancellation: CancellationSignal,
    ) -> DownloadResponse: ...


class TransportFailure(RuntimeError):
    """Erro sanitizado do transporte sem URL, cabeçalhos ou corpo da resposta."""

    def __init__(self, code: str = "TRANSPORT_FAILED", *, retryable: bool = True) -> None:
        self.code = code
        self.retryable = retryable
        super().__init__(code)
