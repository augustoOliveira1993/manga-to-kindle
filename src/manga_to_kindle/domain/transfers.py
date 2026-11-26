"""Tipos de domínio para ações explícitas de envio externo."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class ExportTransferArtifact:
    id: UUID
    export_id: UUID
    package_id: UUID
    format: str
    path: Path
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if self.format not in {"epub", "cbz"}:
            raise DomainValidationError("O formato do artefato exportado não é suportado.")
        if not self.path.is_absolute() or self.size_bytes <= 0:
            raise DomainValidationError("Os dados do artefato exportado são inválidos.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise DomainValidationError("O checksum do artefato exportado é inválido.")


@dataclass(frozen=True, slots=True)
class ManualFlowResult:
    artifact: ExportTransferArtifact
    directory_opened: bool
    page_opened: bool


class TlsMode(StrEnum):
    STARTTLS = "starttls"
    IMPLICIT = "implicit"


class TransferState(StrEnum):
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    TRANSMITTING = "transmitting"
    ACCEPTED_BY_SMTP = "accepted_by_smtp"
    REJECTED_TEMPORARY = "rejected_temporary"
    REJECTED_PERMANENT = "rejected_permanent"
    FAILED_BEFORE_SUBMISSION = "failed_before_submission"
    CANCELLED_BEFORE_SUBMISSION = "cancelled_before_submission"
    UNKNOWN = "unknown"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class SmtpProfile:
    host: str
    port: int
    tls_mode: TlsMode
    sender: str
    recipient: str
    username: str | None
    credential_ref: str | None
    sender_authorized: bool
    recipient_confirmed: bool

    def __post_init__(self) -> None:
        if not _valid_host(self.host) or not 1 <= self.port <= 65535:
            raise DomainValidationError("O servidor SMTP ou a porta são inválidos.")
        if not _valid_email(self.sender) or not _valid_email(self.recipient):
            raise DomainValidationError("Informe um remetente e um destino Kindle válidos.")
        if self.username is not None:
            if not self.username.strip() or self.username != self.username.strip():
                raise DomainValidationError("O usuário SMTP é inválido.")
            if self.credential_ref is None:
                raise DomainValidationError("O segredo SMTP precisa estar no cofre do Windows.")
        elif self.credential_ref is not None:
            raise DomainValidationError("A referência do cofre requer usuário SMTP.")
        if self.credential_ref is not None:
            try:
                UUID(self.credential_ref)
            except ValueError:
                raise DomainValidationError("A referência de credencial não é válida.") from None
        if not self.sender_authorized or not self.recipient_confirmed:
            raise DomainValidationError(
                "A autorização do remetente e do destino precisa ser confirmada pela pessoa usuária."
            )


@dataclass(frozen=True, slots=True)
class TransferJob:
    id: UUID
    artifact_id: UUID
    export_id: UUID
    artifact_sha256: str
    artifact_size_bytes: int
    state: TransferState
    stage: str
    host: str
    port: int
    tls_mode: TlsMode
    sender: str
    masked_recipient: str
    consented_at: datetime
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    smtp_code: int | None = None


@dataclass(frozen=True, slots=True)
class TransferHistoryItem:
    job: TransferJob
    filename: str


def mask_email(address: str) -> str:
    local, domain = address.rsplit("@", maxsplit=1)
    visible = local[:1] if local else ""
    return f"{visible}***@{domain}"


def _valid_email(value: str) -> bool:
    if len(value) > 254 or value != value.strip() or any(ch.isspace() for ch in value):
        return False
    local, separator, domain = value.partition("@")
    return bool(
        separator
        and local
        and domain
        and "@" not in domain
        and re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local)
        and re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", domain)
    )


def _valid_host(value: str) -> bool:
    return bool(
        value
        and value == value.strip()
        and len(value) <= 253
        and re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", value)
    )
