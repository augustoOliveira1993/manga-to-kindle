"""Validação sintática local para o formulário de demonstração."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class UrlValidationResult:
    valid: bool
    code: str | None = None


def validate_http_url(value: str) -> UrlValidationResult:
    """Aceita somente URLs HTTP(S) bem formadas; não resolve nem acessa o host."""

    candidate = value.strip()
    if not candidate or any(character.isspace() for character in candidate):
        return UrlValidationResult(valid=False, code="INVALID_URL")
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return UrlValidationResult(valid=False, code="INVALID_URL")
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (port is not None and not 1 <= port <= 65535)
    ):
        return UrlValidationResult(valid=False, code="INVALID_URL")
    return UrlValidationResult(valid=True)

