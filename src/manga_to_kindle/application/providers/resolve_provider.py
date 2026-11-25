"""Resolve uma URL para exatamente um provider sem emitir rede ou log sensível."""

from __future__ import annotations

from dataclasses import dataclass

from manga_to_kindle.application.providers.normalize_url import normalize_url
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.providers import (
    MangaProvider,
    NormalizedUrl,
    ProviderError,
)


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    provider: MangaProvider
    url: NormalizedUrl


def resolve_provider(value: str, registry: ProviderRegistry) -> ResolvedProvider:
    normalized = normalize_url(value)
    return ResolvedProvider(registry.resolve(normalized), normalized)


def provider_error_message(error: ProviderError) -> str:
    return provider_error_message_for_code(error.code.value)


def provider_error_message_for_code(code: str) -> str:
    messages = {
        "INVALID_URL": "O endereço informado é inválido. Confira o formato HTTP ou HTTPS.",
        "UNSUPPORTED_SCHEME": "Use um endereço HTTP ou HTTPS.",
        "UNSUPPORTED_SOURCE": (
            "Esta fonte não é suportada por um provedor autorizado e configurado."
        ),
        "AMBIGUOUS_PROVIDER": (
            "Mais de um provedor atende a este endereço; a consulta foi interrompida."
        ),
        "UNSAFE_DESTINATION": "O destino não passou pela validação de segurança.",
        "REDIRECT_REJECTED": "O redirecionamento foi bloqueado pela política de segurança.",
        "CAPABILITY_UNAVAILABLE": "A operação não está autorizada para esta fonte.",
        "ACCESS_RESTRICTED": "A fonte exige uma permissão ou acesso que não está disponível.",
        "RATE_LIMITED": "A fonte atingiu o limite de consultas. Tente novamente mais tarde.",
        "CONTENT_UNAVAILABLE": "O conteúdo solicitado não está disponível.",
        "PROVIDER_UNAVAILABLE": "A fonte está temporariamente indisponível.",
        "PROVIDER_RESPONSE_INVALID": "A resposta da fonte não passou pela validação.",
    }
    return messages.get(code, "A consulta foi interrompida por uma falha segura.")
