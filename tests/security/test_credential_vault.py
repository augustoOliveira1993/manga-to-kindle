from __future__ import annotations

from uuid import uuid4

import pytest

from manga_to_kindle.infrastructure.security.credential_vault import (
    CredentialMissing,
    VaultUnavailable,
    WindowsCredentialVault,
)


class MemoryCredentialApi:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def write(self, target: str, secret: bytes) -> None:
        self.values[target] = secret

    def read(self, target: str) -> bytes | None:
        return self.values.get(target)

    def delete(self, target: str) -> None:
        self.values.pop(target, None)


def test_vault_round_trip_and_delete_use_only_opaque_target_reference() -> None:
    api = MemoryCredentialApi()
    vault = WindowsCredentialVault(api)
    reference = str(uuid4())
    sentinel = "private-test-secret"

    vault.store(reference, sentinel)
    assert vault.get(reference) == sentinel
    assert sentinel.encode() not in api.values
    assert len(api.values) == 1

    vault.delete(reference)
    with pytest.raises(CredentialMissing):
        vault.get(reference)


def test_vault_rejects_secret_larger_than_windows_limit_without_storing_it() -> None:
    api = MemoryCredentialApi()
    vault = WindowsCredentialVault(api)

    with pytest.raises(VaultUnavailable):
        vault.store(str(uuid4()), "x" * 2561)

    assert api.values == {}


def test_vault_rejects_non_uuid_references() -> None:
    vault = WindowsCredentialVault(MemoryCredentialApi())

    with pytest.raises(VaultUnavailable):
        vault.get("smtp-password")


def test_vault_rejects_empty_or_nul_secrets() -> None:
    api = MemoryCredentialApi()
    vault = WindowsCredentialVault(api)

    with pytest.raises(VaultUnavailable):
        vault.store(str(uuid4()), "")
    with pytest.raises(VaultUnavailable):
        vault.store(str(uuid4()), "a\x00b")
    assert api.values == {}
