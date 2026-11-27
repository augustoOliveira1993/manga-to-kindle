from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from manga_to_kindle.application.settings.device_profiles import (
    DeviceProfileError,
    ListDeviceProfiles,
    RemoveDeviceProfile,
    SaveDeviceProfile,
)
from manga_to_kindle.application.settings.preferences import (
    PreferenceError,
    SaveApplicationPreferences,
)
from manga_to_kindle.domain.settings import (
    BASIC_10_PROFILE_ID,
    FACTORY_DEVICE_PROFILES,
    ApplicationPreferences,
    DeviceProfileSettings,
)


class MemorySettingsStore:
    def __init__(self) -> None:
        self.profiles: dict[UUID, DeviceProfileSettings] = {}
        self.preferences: ApplicationPreferences | None = None

    def list_custom_profiles(self) -> tuple[DeviceProfileSettings, ...]:
        return tuple(self.profiles.values())

    def save_custom_profile(self, profile: DeviceProfileSettings) -> None:
        self.profiles[profile.id] = profile

    def delete_custom_profile(self, profile_id: UUID) -> bool:
        return self.profiles.pop(profile_id, None) is not None

    def get_preferences(self) -> ApplicationPreferences | None:
        return self.preferences

    def save_preferences(self, preferences: ApplicationPreferences) -> None:
        self.preferences = preferences


def test_factory_profiles_are_read_only_and_duplicates_are_customizable() -> None:
    store = MemorySettingsStore()
    save = SaveDeviceProfile(store)
    listed = ListDeviceProfiles(store).execute()
    source = listed[1]

    custom = save.duplicate(source.id, "Meu Kindle")
    edited = DeviceProfileSettings(
        id=custom.id,
        name=custom.name,
        model=custom.model,
        generation=None,
        width=900,
        height=1200,
    )
    save.execute(edited)

    assert listed[:3] == FACTORY_DEVICE_PROFILES
    assert store.profiles[custom.id] == edited
    assert edited.built_in is False
    with pytest.raises(DeviceProfileError):
        save.execute(source)


def test_active_profile_cannot_be_removed_until_another_profile_is_selected(
    tmp_path: Path,
) -> None:
    store = MemorySettingsStore()
    profile = DeviceProfileSettings(
        id=UUID("d2f8400c-f9ec-4cbd-a8d7-1e9d2400c13b"),
        name="Perfil ativo",
        model="Leitor local",
        generation=None,
        width=600,
        height=800,
    )
    store.save_custom_profile(profile)
    store.preferences = _preferences(tmp_path, profile.id)
    remove = RemoveDeviceProfile(store, store)

    with pytest.raises(DeviceProfileError):
        remove.execute(profile.id)
    store.save_preferences(_preferences(tmp_path, BASIC_10_PROFILE_ID))
    assert remove.execute(profile.id) is True
    assert not store.profiles


def test_preferences_reject_missing_profile_and_nonexistent_directory(tmp_path: Path) -> None:
    store = MemorySettingsStore()
    existing = tmp_path / "downloads"
    existing.mkdir()
    exports = tmp_path / "exports"
    exports.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    save = SaveApplicationPreferences(store, profile_lookup=store)
    valid = _preferences(tmp_path, BASIC_10_PROFILE_ID)

    with pytest.raises(PreferenceError, match="perfil"):
        save.execute(
            ApplicationPreferences(
                selected_profile_id=UUID("d2f8400c-f9ec-4cbd-a8d7-1e9d2400c13b"),
                download_directory=valid.download_directory,
                export_directory=valid.export_directory,
                cache_directory=valid.cache_directory,
            )
        )
    with pytest.raises(PreferenceError):
        save.execute(
            ApplicationPreferences(
                selected_profile_id=BASIC_10_PROFILE_ID,
                download_directory=valid.download_directory,
                export_directory=tmp_path / "missing",
                cache_directory=valid.cache_directory,
            )
        )


def _preferences(root: Path, profile_id: UUID) -> ApplicationPreferences:
    return ApplicationPreferences(
        selected_profile_id=profile_id,
        download_directory=root / "downloads",
        export_directory=root / "exports",
        cache_directory=root / "cache",
    )
