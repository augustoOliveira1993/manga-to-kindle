"""Registro determinístico de provedores internos explicitamente configurados."""

from __future__ import annotations

from collections.abc import Iterable

from manga_to_kindle.domain.providers import (
    AmbiguousProvider,
    MangaProvider,
    NormalizedUrl,
    ProviderResponseInvalid,
    UnsafeDestination,
    UnsupportedSource,
)


class ProviderRegistry:
    def __init__(self, providers: Iterable[MangaProvider]) -> None:
        registered = tuple(providers)
        if len({provider.provider_id for provider in registered}) != len(registered):
            raise ValueError("IDs de provedores registrados precisam ser únicos.")
        self._providers = registered

    @property
    def providers(self) -> tuple[MangaProvider, ...]:
        return self._providers

    def resolve(self, url: NormalizedUrl) -> MangaProvider:
        matches: list[MangaProvider] = []
        for provider in self._providers:
            try:
                supported = provider.supports(url)
            except Exception:
                raise ProviderResponseInvalid() from None
            if supported:
                capabilities = provider.capabilities
                if (
                    url.scheme not in capabilities.allowed_schemes
                    or url.host not in capabilities.allowed_hosts
                ):
                    raise ProviderResponseInvalid()
                if url.port not in capabilities.allowed_ports:
                    raise UnsafeDestination()
                matches.append(provider)
        if not matches:
            raise UnsupportedSource()
        if len(matches) > 1:
            raise AmbiguousProvider()
        return matches[0]

    def by_id(self, provider_id: str) -> MangaProvider:
        """Resolve somente um provedor previamente registrado pelo ID persistido."""
        matches = tuple(
            provider for provider in self._providers if provider.provider_id == provider_id
        )
        if not matches:
            raise UnsupportedSource()
        if len(matches) > 1:
            raise AmbiguousProvider()
        return matches[0]
