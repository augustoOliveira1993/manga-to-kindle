"""Read, validate, and reset local application preferences."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from manga_to_kindle.domain.settings import (
    ApplicationPreferences,
    DeviceProfileSettings,
    factory_profile,
)


class PreferencesStore(Protocol):
    def get_preferences(self) -> ApplicationPreferences | None: ...

    def save_preferences(self, preferences: ApplicationPreferences) -> None: ...


class DeviceProfileLookup(Protocol):
    def list_custom_profiles(self) -> tuple[DeviceProfileSettings, ...]: ...


class PreferenceError(ValueError):
    code = "APPLICATION_PREFERENCES_INVALID"


class DirectoryAccessVerifier(Protocol):
    def verify(self, path: Path) -> None: ...


class WritableDirectoryVerifier:
    def verify(self, path: Path) -> None:
        if path.is_symlink() or not path.exists() or not path.is_dir():
            raise PreferenceError("Escolha uma pasta existente e acessível para esta finalidade.")
        if not os.access(path, os.W_OK):
            raise PreferenceError("A pasta não permite gravação neste momento.") from None


class PreferencePaths(Protocol):
    @property
    def data(self) -> Path: ...

    @property
    def cache(self) -> Path: ...


def default_preferences(paths: PreferencePaths) -> ApplicationPreferences:
    return ApplicationPreferences(
        download_directory=paths.data / "downloads",
        export_directory=paths.data / "exports",
        cache_directory=paths.cache,
    )


class GetApplicationPreferences:
    def __init__(self, store: PreferencesStore, paths: PreferencePaths) -> None:
        self._store = store
        self._defaults = default_preferences(paths)

    def execute(self) -> ApplicationPreferences:
        stored = self._store.get_preferences()
        if stored is not None:
            return stored
        self._store.save_preferences(self._defaults)
        return self._defaults


class SaveApplicationPreferences:
    def __init__(
        self,
        store: PreferencesStore,
        verifier: DirectoryAccessVerifier | None = None,
        profile_lookup: DeviceProfileLookup | None = None,
    ) -> None:
        self._store = store
        self._verifier = verifier or WritableDirectoryVerifier()
        self._profile_lookup = profile_lookup

    def execute(self, preferences: ApplicationPreferences) -> None:
        if (
            self._profile_lookup is not None
            and factory_profile(preferences.selected_profile_id) is None
            and preferences.selected_profile_id
            not in {profile.id for profile in self._profile_lookup.list_custom_profiles()}
        ):
            raise PreferenceError("Selecione um perfil de dispositivo que ainda exista.")
        for path in (
            preferences.download_directory,
            preferences.export_directory,
            preferences.cache_directory,
        ):
            if path is None:
                raise PreferenceError("As pastas padrão precisam estar definidas.")
            self._verifier.verify(path.resolve(strict=False))
        self._store.save_preferences(preferences)


class ResetPreferences:
    def __init__(self, store: PreferencesStore, paths: PreferencePaths) -> None:
        self._store = store
        self._defaults = default_preferences(paths)

    def execute(self, *, confirmed: bool) -> ApplicationPreferences:
        if not confirmed:
            raise PreferenceError("A restauração dos padrões não foi confirmada.")
        try:
            self._store.save_preferences(self._defaults)
        except Exception:
            raise PreferenceError("Não foi possível restaurar os valores padrão.") from None
        return self._defaults
