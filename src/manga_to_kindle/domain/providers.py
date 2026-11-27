"""Contratos de domínio para fontes externas e referências remotas."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga


@dataclass(frozen=True, slots=True)
class NormalizedUrl:
    """URL HTTP(S) canônica; query fica fora da representação de diagnóstico."""

    scheme: str
    host: str
    port: int
    path: str
    query: str = field(repr=False)
    explicit_port: bool = False

    def __post_init__(self) -> None:
        if self.scheme not in {"http", "https"} or not self.host:
            raise ValueError("NormalizedUrl exige esquema e host HTTP(S) válidos.")
        if not 1 <= self.port <= 65535:
            raise ValueError("A porta normalizada está fora do intervalo permitido.")

    @property
    def authority(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        standard_port = 80 if self.scheme == "http" else 443
        return host if self.port == standard_port else f"{host}:{self.port}"

    def render(self) -> str:
        from urllib.parse import urlunsplit

        return urlunsplit((self.scheme, self.authority, self.path, self.query, ""))

    def __repr__(self) -> str:
        return (
            f"NormalizedUrl(scheme={self.scheme!r}, host={self.host!r}, "
            f"port={self.port!r}, path='<redacted>')"
        )


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Capacidades e limites declarados; permissão de download fecha por padrão."""

    provider_id: str
    allowed_hosts: frozenset[str]
    allowed_ports: frozenset[int] = frozenset({80, 443})
    allowed_schemes: frozenset[str] = frozenset({"https"})
    metadata: bool = False
    chapters: bool = False
    page_references: bool = False
    simulated: bool = False
    requires_authentication: bool = False
    download_authorized: bool = False
    authorization_evidence: str | None = None
    authorization_reviewed_on: date | None = None
    authorization_scope: str | None = None
    requests_per_minute: int | None = None
    required_attribution: str | None = None
    removal_policy: str | None = None
    catalog_query_authorized: bool = False
    catalog_query_evidence: str | None = None
    catalog_query_reviewed_on: date | None = None
    catalog_query_scope: str | None = None
    periodic_catalog_updates_authorized: bool = False
    minimum_catalog_update_interval_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("O provedor precisa de um identificador.")
        if not self.allowed_hosts:
            raise ValueError("O provedor precisa declarar hosts permitidos.")
        normalized_hosts = frozenset(
            host.encode("idna").decode("ascii").lower().rstrip(".") for host in self.allowed_hosts
        )
        object.__setattr__(self, "allowed_hosts", normalized_hosts)
        if not self.allowed_schemes or not self.allowed_schemes <= {"http", "https"}:
            raise ValueError("Esquemas permitidos devem ser HTTP ou HTTPS.")
        if not self.allowed_ports or any(not 1 <= port <= 65535 for port in self.allowed_ports):
            raise ValueError("O conjunto de portas permitidas é inválido.")
        if self.requests_per_minute is not None and self.requests_per_minute < 1:
            raise ValueError("O limite de requisições precisa ser positivo.")
        if self.download_authorized and not all(
            (
                self.authorization_evidence,
                self.authorization_reviewed_on,
                self.authorization_scope,
            )
        ):
            raise ValueError("Download exige evidência, revisão e escopo autorizados.")
        if self.catalog_query_authorized and not all(
            (
                self.catalog_query_evidence,
                self.catalog_query_reviewed_on,
                self.catalog_query_scope,
            )
        ):
            raise ValueError("Consulta de catálogo exige evidência, revisão e escopo autorizados.")
        if self.catalog_query_authorized and self.requests_per_minute is None:
            raise ValueError("Consulta de catálogo exige limite de requisições documentado.")
        if self.periodic_catalog_updates_authorized and not self.catalog_query_enabled:
            raise ValueError("Atualização periódica exige consulta de catálogo autorizada.")
        if self.minimum_catalog_update_interval_seconds is not None and (
            type(self.minimum_catalog_update_interval_seconds) is not int
            or self.minimum_catalog_update_interval_seconds < 1
        ):
            raise ValueError("O intervalo mínimo da fonte precisa ser positivo.")
        if self.periodic_catalog_updates_authorized and (
            self.minimum_catalog_update_interval_seconds is None
        ):
            raise ValueError("Atualização periódica exige intervalo mínimo documentado.")

    @property
    def download_enabled(self) -> bool:
        return self.download_authorized and all(
            (
                self.authorization_evidence,
                self.authorization_reviewed_on,
                self.authorization_scope,
            )
        )

    @property
    def catalog_query_enabled(self) -> bool:
        return (
            not self.simulated
            and self.metadata
            and self.chapters
            and self.catalog_query_authorized
            and self.requests_per_minute is not None
            and all(
                (
                    self.catalog_query_evidence,
                    self.catalog_query_reviewed_on,
                    self.catalog_query_scope,
                )
            )
        )

    @property
    def periodic_catalog_updates_enabled(self) -> bool:
        return (
            self.catalog_query_enabled
            and self.periodic_catalog_updates_authorized
            and self.minimum_catalog_update_interval_seconds is not None
        )


@dataclass(frozen=True, slots=True)
class ProviderPageReference:
    source_id: str
    position: int
    source_reference: str = field(repr=False)
    destination: NormalizedUrl = field(repr=False)
    simulated: bool = False

    def __post_init__(self) -> None:
        if not self.source_id.strip() or self.position < 0:
            raise ValueError("A referência de página precisa de ID e posição válida.")
        if not self.source_reference.strip():
            raise ValueError("A referência de origem não pode ser vazia.")


@dataclass(frozen=True, slots=True)
class ChapterCatalogResponse:
    """Snapshot de resposta; paginação incompleta nunca pode substituir o catálogo local."""

    chapters: tuple[Chapter, ...]
    complete: bool

    def __post_init__(self) -> None:
        if type(self.complete) is not bool:
            raise ValueError("A resposta precisa declarar se o catálogo está completo.")


class ProviderErrorCode(StrEnum):
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_SCHEME = "UNSUPPORTED_SCHEME"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"
    AMBIGUOUS_PROVIDER = "AMBIGUOUS_PROVIDER"
    UNSAFE_DESTINATION = "UNSAFE_DESTINATION"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    RATE_LIMITED = "RATE_LIMITED"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_RESPONSE_INVALID = "PROVIDER_RESPONSE_INVALID"


class ProviderError(Exception):
    code: ProviderErrorCode

    def __init__(
        self,
        code: ProviderErrorCode,
        *,
        retryable: bool = False,
        safe_message_key: str | None = None,
    ) -> None:
        self.code = code
        self.retryable = retryable
        self.safe_message_key = safe_message_key or code.value
        super().__init__(code.value)


class InvalidUrl(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.INVALID_URL)


class UnsupportedScheme(InvalidUrl):
    def __init__(self) -> None:
        ProviderError.__init__(self, ProviderErrorCode.UNSUPPORTED_SCHEME)


class UnsupportedSource(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.UNSUPPORTED_SOURCE)


class AmbiguousProvider(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.AMBIGUOUS_PROVIDER)


class UnsafeDestination(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.UNSAFE_DESTINATION)


class RedirectRejected(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.REDIRECT_REJECTED)


class CapabilityUnavailable(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.CAPABILITY_UNAVAILABLE)


class AccessRestricted(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.ACCESS_RESTRICTED)


class RateLimited(ProviderError):
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("Retry-After não pode ser negativo.")
        self.retry_after_seconds = retry_after_seconds
        super().__init__(ProviderErrorCode.RATE_LIMITED, retryable=True)


class ContentUnavailable(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.CONTENT_UNAVAILABLE)


class ProviderUnavailable(ProviderError):
    def __init__(self, *, retryable: bool = True) -> None:
        super().__init__(ProviderErrorCode.PROVIDER_UNAVAILABLE, retryable=retryable)


class ProviderResponseInvalid(ProviderError):
    def __init__(self) -> None:
        super().__init__(ProviderErrorCode.PROVIDER_RESPONSE_INVALID)


@runtime_checkable
class MangaProvider(Protocol):
    provider_id: str
    capabilities: ProviderCapabilities

    def supports(self, url: NormalizedUrl) -> bool: ...

    def get_manga(self, url: NormalizedUrl) -> Manga: ...

    def get_chapters(self, manga: Manga) -> tuple[Chapter, ...]: ...

    def get_pages(self, chapter: Chapter) -> tuple[ProviderPageReference, ...]: ...


@runtime_checkable
class CatalogUpdateProvider(MangaProvider, Protocol):
    """Contrato opcional de consulta completa para a atualização F010."""

    def get_chapter_catalog(
        self,
        manga: Manga,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> ChapterCatalogResponse: ...
