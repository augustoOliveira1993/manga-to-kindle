import json
from pathlib import Path

import pytest

from manga_to_kindle.infrastructure.config.settings import (
    AppSettings,
    InvalidSettingsError,
    load_or_create_settings,
)
from manga_to_kindle.infrastructure.paths import AppPaths


def test_defaults_match_the_foundation_policy() -> None:
    settings = AppSettings()

    assert settings.log_max_bytes == 5 * 1024 * 1024
    assert settings.log_backup_count == 3
    assert settings.theme == "light"


def test_first_load_writes_defaults_atomically(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path)
    paths.ensure()

    settings = load_or_create_settings(paths)

    assert settings == AppSettings()
    assert json.loads(paths.settings_file.read_text(encoding="utf-8")) == {
        "log_max_bytes": 5 * 1024 * 1024,
        "log_backup_count": 3,
        "theme": "light",
    }


def test_invalid_configuration_is_preserved(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path)
    paths.ensure()
    original = b'{"log_max_bytes": 0, "log_backup_count": 3}\n'
    paths.settings_file.write_bytes(original)

    with pytest.raises(InvalidSettingsError):
        load_or_create_settings(paths)

    assert paths.settings_file.read_bytes() == original
