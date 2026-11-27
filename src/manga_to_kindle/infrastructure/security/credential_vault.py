"""Adaptador do Gerenciador de Credenciais do Windows para segredos SMTP."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from typing import Protocol
from uuid import UUID

from manga_to_kindle.application.transfers.ports import CredentialMissing, VaultUnavailable


class _CredentialApi(Protocol):
    def write(self, target: str, secret: bytes) -> None: ...

    def read(self, target: str) -> bytes | None: ...

    def delete(self, target: str) -> None: ...


class WindowsCredentialVault:
    """Guarda segredos em credenciais genéricas no vault do usuário atual."""

    _TARGET_PREFIX = "MangaToKindle.SMTP."
    _MAX_SECRET_BYTES = 5 * 512

    def __init__(self, api: _CredentialApi | None = None) -> None:
        if api is None:
            if os.name != "nt":
                raise VaultUnavailable("O cofre de credenciais do Windows não está disponível.")
            api = _WinCredentialApi()
        self._api = api

    def store(self, credential_ref: str, secret: str) -> None:
        target = _target_name(credential_ref)
        if not secret or "\x00" in secret:
            raise VaultUnavailable("A credencial não pode ser vazia ou conter NUL.")
        encoded = secret.encode("utf-8")
        if len(encoded) > self._MAX_SECRET_BYTES:
            raise VaultUnavailable("A credencial excede o limite do cofre do Windows.")
        self._api.write(target, encoded)

    def get(self, credential_ref: str) -> str:
        raw = self._api.read(_target_name(credential_ref))
        if raw is None:
            raise CredentialMissing("A credencial SMTP não está disponível no cofre do Windows.")
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise VaultUnavailable(
                "A credencial SMTP do cofre não tem codificação válida."
            ) from None

    def delete(self, credential_ref: str) -> None:
        self._api.delete(_target_name(credential_ref))


def _target_name(credential_ref: str) -> str:
    try:
        normalized = str(UUID(credential_ref))
    except (TypeError, ValueError):
        raise VaultUnavailable("A referência do cofre é inválida.") from None
    return f"{WindowsCredentialVault._TARGET_PREFIX}{normalized}"


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class _WinCredentialApi:
    _GENERIC = 1
    _PERSIST_LOCAL_MACHINE = 2
    _ERROR_NOT_FOUND = 1168

    def __init__(self) -> None:
        try:
            self._library = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        except (AttributeError, OSError):
            raise VaultUnavailable(
                "O cofre de credenciais do Windows não está disponível."
            ) from None
        self._library.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        self._library.CredWriteW.restype = wintypes.BOOL
        self._library.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)),
        ]
        self._library.CredReadW.restype = wintypes.BOOL
        self._library.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._library.CredDeleteW.restype = wintypes.BOOL
        self._library.CredFree.argtypes = [ctypes.c_void_p]
        self._library.CredFree.restype = None

    def write(self, target: str, secret: bytes) -> None:
        buffer = ctypes.create_string_buffer(secret, len(secret))
        credential = _CREDENTIALW(
            Flags=0,
            Type=self._GENERIC,
            TargetName=target,
            Comment="Manga to Kindle SMTP",
            LastWritten=_FILETIME(),
            CredentialBlobSize=len(secret),
            CredentialBlob=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=self._PERSIST_LOCAL_MACHINE,
            AttributeCount=0,
            Attributes=None,
            TargetAlias=None,
            UserName=None,
        )
        if not self._library.CredWriteW(ctypes.byref(credential), 0):
            raise VaultUnavailable("O Windows não conseguiu gravar a credencial no cofre.")

    def read(self, target: str) -> bytes | None:
        credential_pointer = ctypes.POINTER(_CREDENTIALW)()
        if not self._library.CredReadW(
            target,
            self._GENERIC,
            0,
            ctypes.byref(credential_pointer),
        ):
            if ctypes.get_last_error() == self._ERROR_NOT_FOUND:
                return None
            raise VaultUnavailable("O Windows não conseguiu ler a credencial do cofre.")
        try:
            credential = credential_pointer.contents
            if credential.CredentialBlobSize > WindowsCredentialVault._MAX_SECRET_BYTES:
                raise VaultUnavailable("A credencial no cofre excede o limite permitido.")
            if credential.CredentialBlobSize == 0:
                return b""
            return ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        finally:
            self._library.CredFree(credential_pointer)

    def delete(self, target: str) -> None:
        if self._library.CredDeleteW(target, self._GENERIC, 0):
            return
        if ctypes.get_last_error() == self._ERROR_NOT_FOUND:
            return
        raise VaultUnavailable("O Windows não conseguiu remover a credencial do cofre.")
