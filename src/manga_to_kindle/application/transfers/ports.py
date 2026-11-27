"""Ports and errors used by the SMTP transfer application services."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from manga_to_kindle.domain.transfers import (
    SmtpProfile,
    SmtpTransportResult,
)


class VaultUnavailable(RuntimeError):
    code = "CREDENTIAL_VAULT_UNAVAILABLE"


class CredentialMissing(RuntimeError):
    code = "CREDENTIAL_MISSING"


class CredentialVault(Protocol):
    def store(self, credential_ref: str, secret: str) -> None: ...

    def get(self, credential_ref: str) -> str: ...

    def delete(self, credential_ref: str) -> None: ...


class CancellationPort(Protocol):
    @property
    def cancelled(self) -> bool: ...


class SmtpTransportPort(Protocol):
    def test_connection(self, profile: SmtpProfile, password: str | None) -> None: ...

    def send(
        self,
        *,
        profile: SmtpProfile,
        password: str | None,
        file_path: Path,
        expected_sha256: str,
        expected_size: int,
        cancellation: CancellationPort,
        report_stage: Callable[[str, str], None],
    ) -> SmtpTransportResult: ...


def estimate_message_size(file_size: int, filename: str) -> int:
    if file_size <= 0:
        return 0
    encoded_chars = 4 * ((file_size + 2) // 3)
    line_break_bytes = 2 * ((encoded_chars + 75) // 76)
    header_and_body_allowance = 8192 + (len(filename.encode("utf-8")) * 3)
    return encoded_chars + line_break_bytes + header_and_body_allowance


MAX_KINDLE_EMAIL_BYTES = 50_000_000
