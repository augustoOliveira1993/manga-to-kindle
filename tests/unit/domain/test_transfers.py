from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.transfers import (
    ExportTransferArtifact,
    SmtpProfile,
    TlsMode,
    TransferState,
    mask_email,
)


def _profile(**overrides: object) -> SmtpProfile:
    values: dict[str, object] = {
        "host": "smtp.example.test",
        "port": 587,
        "tls_mode": TlsMode.STARTTLS,
        "sender": "reader@example.test",
        "recipient": "device@kindle.com",
        "username": None,
        "credential_ref": None,
        "sender_authorized": True,
        "recipient_confirmed": True,
    }
    values.update(overrides)
    return SmtpProfile(**values)  # type: ignore[arg-type]


def test_profile_requires_tls_and_one_confirmed_valid_recipient() -> None:
    assert _profile().recipient == "device@kindle.com"

    with pytest.raises(DomainValidationError):
        _profile(recipient="not-an-address")
    with pytest.raises(DomainValidationError):
        _profile(sender_authorized=False)
    with pytest.raises(DomainValidationError):
        _profile(port=0)


def test_authenticated_profile_requires_opaque_credential_reference() -> None:
    with pytest.raises(DomainValidationError):
        _profile(username="reader@example.test")

    assert _profile(
        username="reader@example.test",
        credential_ref=str(uuid4()),
    ).username == "reader@example.test"


def test_export_artifact_rejects_bad_checksum_and_relative_path() -> None:
    values: dict[str, object] = {
        "id": uuid4(),
        "export_id": uuid4(),
        "package_id": uuid4(),
        "format": "epub",
        "path": Path("chapter.epub"),
        "sha256": "x" * 64,
        "size_bytes": 1,
    }

    with pytest.raises(DomainValidationError):
        ExportTransferArtifact(**values)  # type: ignore[arg-type]


def test_transfer_state_and_history_mask_the_destination() -> None:
    assert TransferState.ACCEPTED_BY_SMTP.value == "accepted_by_smtp"
    assert mask_email("private-device@kindle.com") == "p***@kindle.com"

