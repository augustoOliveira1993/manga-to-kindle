"""Use cases for built-in and user-created output profiles."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import UUID, uuid4

from manga_to_kindle.domain.settings import (
    FACTORY_DEVICE_PROFILES,
    ApplicationPreferences,
    DeviceProfileSettings,
    factory_profile,
)


class DeviceProfileStore(Protocol):
    def list_custom_profiles(self) -> tuple[DeviceProfileSettings, ...]: ...

    def save_custom_profile(self, profile: DeviceProfileSettings) -> None: ...

    def delete_custom_profile(self, profile_id: UUID) -> bool: ...


class PreferencesStore(Protocol):
    def get_preferences(self) -> ApplicationPreferences | None: ...

    def save_preferences(self, preferences: ApplicationPreferences) -> None: ...


class DeviceProfileError(ValueError):
    code = "DEVICE_PROFILE_INVALID"


class ListDeviceProfiles:
    def __init__(self, store: DeviceProfileStore) -> None:
        self._store = store

    def execute(self) -> tuple[DeviceProfileSettings, ...]:
        return (*FACTORY_DEVICE_PROFILES, *self._store.list_custom_profiles())


class SaveDeviceProfile:
    def __init__(self, store: DeviceProfileStore) -> None:
        self._store = store

    def duplicate(self, profile_id: UUID, name: str) -> DeviceProfileSettings:
        profile = self._get(profile_id)
        copied = replace(profile, id=uuid4(), name=name.strip(), built_in=False)
        self._store.save_custom_profile(copied)
        return copied

    def execute(self, profile: DeviceProfileSettings) -> None:
        if profile.built_in or factory_profile(profile.id) is not None:
            raise DeviceProfileError("Os perfis de fábrica não podem ser editados.")
        self._store.save_custom_profile(profile)

    def _get(self, profile_id: UUID) -> DeviceProfileSettings:
        profile = factory_profile(profile_id)
        if profile is not None:
            return profile
        profile = next(
            (item for item in self._store.list_custom_profiles() if item.id == profile_id),
            None,
        )
        if profile is None:
            raise DeviceProfileError("O perfil selecionado não existe mais.")
        return profile


class RemoveDeviceProfile:
    def __init__(self, store: DeviceProfileStore, preferences: PreferencesStore) -> None:
        self._store = store
        self._preferences = preferences

    def execute(self, profile_id: UUID) -> bool:
        if factory_profile(profile_id) is not None:
            raise DeviceProfileError("Os perfis de fábrica não podem ser removidos.")
        preferences = self._preferences.get_preferences()
        if preferences is not None and preferences.selected_profile_id == profile_id:
            raise DeviceProfileError("Selecione outro perfil antes de remover o perfil ativo.")
        return self._store.delete_custom_profile(profile_id)
