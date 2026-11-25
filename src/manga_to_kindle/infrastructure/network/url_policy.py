"""Validação de destino injetável; não abre sockets nem resolve DNS por conta própria."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urljoin

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.domain.providers import (
    NormalizedUrl,
    ProviderError,
    RedirectRejected,
    UnsafeDestination,
)

type HostResolver = Callable[[str], Sequence[str]]


@dataclass(frozen=True, slots=True)
class ValidatedDestination:
    scheme: str
    hostname: str
    port: int
    approved_addresses: frozenset[str]

    def assert_connected_address(self, address: str) -> None:
        candidate = _parse_public_address(address)
        if candidate not in self.approved_addresses:
            raise UnsafeDestination()


class ExternalUrlPolicy:
    """Valida esquema, host exato, porta, DNS e endereço efetivamente conectado."""

    def __init__(self, resolver: HostResolver | None) -> None:
        self._resolver = resolver

    def validate(
        self,
        url: NormalizedUrl,
        *,
        allowed_hosts: frozenset[str],
        allowed_ports: frozenset[int] = frozenset({80, 443}),
    ) -> ValidatedDestination:
        normalized_hosts = frozenset(
            host.encode("idna").decode("ascii").lower().rstrip(".")
            for host in allowed_hosts
        )
        if url.host not in normalized_hosts or url.port not in allowed_ports:
            raise UnsafeDestination()
        try:
            literal = ipaddress.ip_address(url.host)
        except ValueError:
            literal = None
        if literal is not None:
            addresses: Sequence[str] = (url.host,)
        else:
            if self._resolver is None:
                raise UnsafeDestination()
            try:
                addresses = tuple(self._resolver(url.host))
            except Exception:
                raise UnsafeDestination() from None
        approved = frozenset(_parse_public_address(address) for address in addresses)
        if not approved:
            raise UnsafeDestination()
        return ValidatedDestination(url.scheme, url.host, url.port, approved)

    def validate_redirect_chain(
        self,
        start: NormalizedUrl,
        locations: Sequence[str],
        *,
        allowed_hosts: frozenset[str],
        allowed_ports: frozenset[int] = frozenset({80, 443}),
        max_redirects: int = 5,
    ) -> tuple[NormalizedUrl, ...]:
        if max_redirects < 0 or len(locations) > min(max_redirects, 5):
            raise RedirectRejected()
        try:
            self.validate(
                start,
                allowed_hosts=allowed_hosts,
                allowed_ports=allowed_ports,
            )
            chain = [start]
            current = start
            seen = {start.render()}
            for location in locations:
                target = normalize_url(urljoin(current.render(), location))
                if current.scheme == "https" and target.scheme != "https":
                    raise RedirectRejected()
                rendered = target.render()
                if rendered in seen:
                    raise RedirectRejected()
                self.validate(
                    target,
                    allowed_hosts=allowed_hosts,
                    allowed_ports=allowed_ports,
                )
                chain.append(target)
                seen.add(rendered)
                current = target
            return tuple(chain)
        except RedirectRejected:
            raise
        except ProviderError:
            raise RedirectRejected() from None


def _parse_public_address(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise UnsafeDestination() from None
    if isinstance(address, ipaddress.IPv6Address) and address.scope_id is not None:
        raise UnsafeDestination()
    effective: ipaddress.IPv4Address | ipaddress.IPv6Address
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        effective = address.ipv4_mapped
    else:
        effective = address
    if not effective.is_global:
        raise UnsafeDestination()
    return effective.compressed.lower()
