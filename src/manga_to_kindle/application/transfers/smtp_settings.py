"""Casos de uso para guardar perfil SMTP sem persistir o segredo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from manga_to_kindle.application.transfers.ports import (
    CredentialVault,
    VaultUnavailable,
)
from manga_to_kindle.domain.transfers import SmtpProfile, TlsMode


class SmtpProfileRepository(Protocol):
    def get_profile(self) -> SmtpProfile | None: ...

    def save_profile(self, profile: SmtpProfile) -> str | None: ...

    def remove_profile(self) -> str | None: ...


class SmtpConnectionPort(Protocol):
    def test_connection(self, profile: SmtpProfile, password: str | None) -> None: ...


class SmtpProfileConfigurationError(RuntimeError):
    code = "SMTP_PROFILE_INVALID"


@dataclass(frozen=True, slots=True)
class ProfileSaveResult:
    profile: SmtpProfile
    previous_credential_removed: bool


class SaveSmtpProfile:
    def __init__(self, repository: SmtpProfileRepository, vault: CredentialVault) -> None:
        self._repository = repository
        self._vault = vault

    def execute(
        self,
        *,
        host: str,
        port: int,
        tls_mode: TlsMode,
        sender: str,
        recipient: str,
        username: str | None,
        password: str,
        sender_authorized: bool,
        recipient_confirmed: bool,
    ) -> ProfileSaveResult:
        normalized_username = username.strip() if username and username.strip() else None
        host = host.strip()
        sender = sender.strip()
        recipient = recipient.strip()
        # Validate all user-controlled fields before a new secret reaches the vault.
        SmtpProfile(
            host=host,
            port=port,
            tls_mode=tls_mode,
            sender=sender,
            recipient=recipient,
            username=None,
            credential_ref=None,
            sender_authorized=sender_authorized,
            recipient_confirmed=recipient_confirmed,
        )
        current = self._repository.get_profile()
        credential_ref: str | None = None
        new_ref: str | None = None
        if normalized_username is not None:
            if password:
                new_ref = str(uuid4())
                self._vault.store(new_ref, password)
                credential_ref = new_ref
            elif current is not None and _same_authentication_target(
                current,
                host=host,
                port=port,
                tls_mode=tls_mode,
                sender=sender,
                recipient=recipient,
                username=normalized_username,
            ):
                credential_ref = current.credential_ref
            else:
                raise SmtpProfileConfigurationError(
                    "Informe a senha para a nova conta SMTP; segredos não são "
                    "recuperados para a tela."
                )
        elif password:
            raise SmtpProfileConfigurationError("Informe o usuário SMTP antes de salvar a senha.")

        profile = SmtpProfile(
            host=host,
            port=port,
            tls_mode=tls_mode,
            sender=sender,
            recipient=recipient,
            username=normalized_username,
            credential_ref=credential_ref,
            sender_authorized=sender_authorized,
            recipient_confirmed=recipient_confirmed,
        )
        try:
            previous_ref = self._repository.save_profile(profile)
        except Exception:
            if new_ref is not None:
                try:
                    self._vault.delete(new_ref)
                except VaultUnavailable:
                    pass
            raise

        removed = True
        if previous_ref is not None and previous_ref != credential_ref:
            try:
                self._vault.delete(previous_ref)
            except VaultUnavailable:
                removed = False
        return ProfileSaveResult(profile, removed)


class RemoveSmtpProfile:
    def __init__(self, repository: SmtpProfileRepository, vault: CredentialVault) -> None:
        self._repository = repository
        self._vault = vault

    def execute(self) -> bool:
        credential_ref = self._repository.remove_profile()
        if credential_ref is None:
            return True
        try:
            self._vault.delete(credential_ref)
        except VaultUnavailable:
            return False
        return True


class TestSmtpConnection:
    __test__ = False

    def __init__(
        self,
        repository: SmtpProfileRepository,
        vault: CredentialVault,
        transport: SmtpConnectionPort,
    ) -> None:
        self._repository = repository
        self._vault = vault
        self._transport = transport

    def execute(self) -> None:
        profile = self._repository.get_profile()
        if profile is None:
            raise SmtpProfileConfigurationError("Salve um perfil SMTP antes de testar a conexão.")
        password = None
        try:
            if profile.credential_ref is not None:
                password = self._vault.get(profile.credential_ref)
            self._transport.test_connection(profile, password)
        except Exception:
            raise SmtpProfileConfigurationError(
                "Não foi possível testar a conexão SMTP com TLS. Confira host, porta e credenciais."
            ) from None
        finally:
            password = None


def _same_authentication_target(
    profile: SmtpProfile,
    *,
    host: str,
    port: int,
    tls_mode: TlsMode,
    sender: str,
    recipient: str,
    username: str,
) -> bool:
    return (
        profile.host == host.strip()
        and profile.port == port
        and profile.tls_mode is tls_mode
        and profile.sender == sender.strip()
        and profile.recipient == recipient.strip()
        and profile.username == username
        and profile.credential_ref is not None
    )
