"""Normalização sintática de URLs sem DNS ou acesso de rede."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

from manga_to_kindle.domain.providers import InvalidUrl, NormalizedUrl, UnsupportedScheme


def normalize_url(value: str) -> NormalizedUrl:
    if not isinstance(value, str):
        raise InvalidUrl()
    candidate = value.strip()
    if not candidate or any(character.isspace() or ord(character) < 32 for character in candidate):
        raise InvalidUrl()
    try:
        parsed = urlsplit(candidate)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise UnsupportedScheme()
        if "@" in parsed.netloc or parsed.username is not None or parsed.password is not None:
            raise InvalidUrl()
        raw_host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        if isinstance(error, (InvalidUrl, UnsupportedScheme)):
            raise
        raise InvalidUrl() from None
    if not raw_host:
        raise InvalidUrl()
    if port is not None and not 1 <= port <= 65535:
        raise InvalidUrl()
    host = _normalize_host(raw_host)
    standard_port = 80 if scheme == "http" else 443
    return NormalizedUrl(
        scheme=scheme,
        host=host,
        port=port or standard_port,
        path=parsed.path or "/",
        query=parsed.query,
        explicit_port=port is not None,
    )


def _normalize_host(value: str) -> str:
    candidate = value.rstrip(".")
    if not candidate or "%" in candidate:
        raise InvalidUrl()
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        if re.fullmatch(r"[0-9.]+", candidate):
            raise InvalidUrl() from None
        try:
            host = candidate.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise InvalidUrl() from None
        if len(host) > 253:
            raise InvalidUrl() from None
        labels = host.split(".")
        if any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or re.fullmatch(r"[a-z0-9-]+", label) is None
            for label in labels
        ):
            raise InvalidUrl() from None
        return host
    if isinstance(address, ipaddress.IPv6Address) and address.scope_id is not None:
        raise InvalidUrl()
    return address.compressed.lower()
