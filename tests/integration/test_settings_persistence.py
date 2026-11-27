from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.application.settings.preferences import GetApplicationPreferences
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.settings import ApplicationPreferences, DeviceProfileSettings
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.settings_repository import (
    SettingsPersistenceError,
    SettingsRepository,
)


def test_preferences_and_custom_profile_persist_after_restart(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path / "profile")
    paths.ensure()
    database = SQLiteDatabase(paths.database_file)
    database.initialize()
    repository = SettingsRepository(database)
    defaults = GetApplicationPreferences(repository, paths).execute()
    profile = DeviceProfileSettings(
        id=uuid4(),
        name="Leitor 900 × 1200",
        model="Perfil personalizado",
        generation=None,
        width=900,
        height=1200,
        ppi=None,
        direction=ReadingDirection.LEFT_TO_RIGHT,
        crop_margins=True,
        quality=84,
    )
    repository.save_custom_profile(profile)
    with pytest.raises(SettingsPersistenceError):
        repository.save_custom_profile(replace(profile, id=uuid4(), name="leitor 900 × 1200"))
    updated_preferences = ApplicationPreferences(
        selected_profile_id=profile.id,
        download_concurrency=1,
        download_directory=defaults.download_directory,
        export_directory=defaults.export_directory,
        cache_directory=defaults.cache_directory,
        cache_limit_bytes=2 * 1024 * 1024 * 1024,
        cache_retention_days=14,
    )
    repository.save_preferences(updated_preferences)
    database.close()

    reopened = SQLiteDatabase(paths.database_file)
    reopened.initialize()
    reopened_repository = SettingsRepository(reopened)

    assert reopened.current_revision() == "0011_mobi_export_artifacts"
    assert reopened_repository.get_preferences() == updated_preferences
    assert reopened_repository.list_custom_profiles() == (profile,)
    reopened.close()


def test_legacy_profile_without_f011_fields_receives_explicit_defaults(tmp_path: Path) -> None:
    from manga_to_kindle.infrastructure.persistence.models import DeviceProfileRecord

    paths = AppPaths.from_root(tmp_path / "profile")
    paths.ensure()
    database = SQLiteDatabase(paths.database_file)
    database.initialize()
    legacy_id = uuid4()
    with database.unit_of_work() as session:
        session.add(DeviceProfileRecord(id=legacy_id, name="Perfil legado", preferences={}))

    (profile,) = SettingsRepository(database).list_custom_profiles()
    assert profile.id == legacy_id
    assert (profile.width, profile.height) == (600, 800)
    assert profile.direction is ReadingDirection.RIGHT_TO_LEFT
    assert profile.crop_margins is False
    database.close()
