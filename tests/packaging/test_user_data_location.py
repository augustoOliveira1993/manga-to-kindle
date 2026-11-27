from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import QStandardPaths

from manga_to_kindle.infrastructure.paths import AppPaths


def test_data_location_comes_from_user_profile_not_install_directory(tmp_path: Path) -> None:
    install_directory = tmp_path / "Programs" / "MangaToKindle"
    user_data_directory = tmp_path / "LocalAppData" / "MangaToKindle" / "MangaToKindle"
    install_directory.mkdir(parents=True)

    with patch.object(
        QStandardPaths,
        "writableLocation",
        return_value=str(user_data_directory),
    ):
        paths = AppPaths.from_qstandardpaths()

    assert paths.root == user_data_directory
    assert paths.root != install_directory
    assert not (install_directory / "data").exists()


def test_data_root_override_is_absolute_and_isolates_packaged_smoke_tests(tmp_path: Path) -> None:
    user_data_directory = tmp_path / "isolated-profile"

    with patch.dict(os.environ, {"MANGA_TO_KINDLE_DATA_ROOT": str(user_data_directory)}):
        paths = AppPaths.from_qstandardpaths()

    assert paths.root == user_data_directory.resolve()


def test_data_root_override_rejects_relative_paths() -> None:
    with patch.dict(os.environ, {"MANGA_TO_KINDLE_DATA_ROOT": "relative-profile"}):
        with pytest.raises(OSError, match="precisa ser absoluta"):
            AppPaths.from_qstandardpaths()
