from __future__ import annotations

import pytest

from manga_to_kindle.application.transfers.smtp_settings import (
    RemoveSmtpProfile,
    SaveSmtpProfile,
    SmtpProfileConfigurationError,
)
from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.transfers import SmtpProfile, TlsMode


class ProfileRepository:
    def __init__(self) -> None:
        self.profile: SmtpProfile | None = None

    def get_profile(self) -> SmtpProfile | None:
        return self.profile

    def save_profile(self, profile: SmtpProfile) -> str | None:
        old = self.profile.credential_ref if self.profile is not None else None
        self.profile = profile
        return old

    def remove_profile(self) -> str | None:
        old = self.profile.credential_ref if self.profile is not None else None
        self.profile = None
        return old


class Vault:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []

    def store(self, reference: str, secret: str) -> None:
        self.values[reference] = secret

    def get(self, reference: str) -> str:
        return self.values[reference]

    def delete(self, reference: str) -> None:
        self.deleted.append(reference)
        self.values.pop(reference, None)


def _save(repository: ProfileRepository, vault: Vault, **overrides: object):
    values: dict[str, object] = {
        "host": "smtp.example.test",
        "port": 587,
        "tls_mode": TlsMode.STARTTLS,
        "sender": "reader@example.test",
        "recipient": "device@kindle.com",
        "username": "reader@example.test",
        "password": "secret-sentinel",
        "sender_authorized": True,
        "recipient_confirmed": True,
    }
    values.update(overrides)
    return SaveSmtpProfile(repository, vault).execute(**values)  # type: ignore[arg-type]


def test_profile_save_stores_only_opaque_reference_and_removal_cleans_vault() -> None:
    repository = ProfileRepository()
    vault = Vault()

    saved = _save(repository, vault)

    assert saved.profile.credential_ref in vault.values
    assert "secret-sentinel" not in repr(saved.profile)
    assert repository.profile == saved.profile
    reference = saved.profile.credential_ref
    assert reference is not None

    assert RemoveSmtpProfile(repository, vault).execute() is True
    assert repository.profile is None
    assert vault.deleted == [reference]
    assert vault.values == {}


def test_same_profile_can_be_saved_without_reentering_password() -> None:
    repository = ProfileRepository()
    vault = Vault()
    original = _save(repository, vault).profile

    saved = _save(repository, vault, password="")

    assert saved.profile.credential_ref == original.credential_ref
    assert len(vault.values) == 1
    assert saved.previous_credential_removed is True


def test_changing_authenticated_host_requires_a_new_password() -> None:
    repository = ProfileRepository()
    vault = Vault()
    _save(repository, vault)

    with pytest.raises(SmtpProfileConfigurationError):
        _save(repository, vault, host="other.example.test", password="")

    assert repository.profile is not None
    assert len(vault.values) == 1


def test_invalid_profile_is_rejected_before_secret_reaches_vault() -> None:
    repository = ProfileRepository()
    vault = Vault()

    with pytest.raises(DomainValidationError):
        _save(repository, vault, recipient="not-an-email")

    assert vault.values == {}
    assert repository.profile is None


def test_removal_reports_vault_cleanup_failure() -> None:
    class BrokenVault(Vault):
        def delete(self, reference: str) -> None:
            from manga_to_kindle.infrastructure.security.credential_vault import VaultUnavailable

            raise VaultUnavailable("unavailable")

    repository = ProfileRepository()
    vault = BrokenVault()
    _save(repository, vault)

    assert RemoveSmtpProfile(repository, vault).execute() is False
    assert repository.profile is None
