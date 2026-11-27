from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.settings import (
    BASIC_10_PROFILE_ID,
    FACTORY_DEVICE_PROFILES,
    GIB,
    MIB,
    ApplicationPreferences,
    DeviceProfileSettings,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "settings"


def _profile(**overrides: object) -> DeviceProfileSettings:
    values: dict[str, object] = {
        "id": uuid4(),
        "name": "Perfil customizado",
        "model": "Perfil personalizado",
        "generation": None,
        "width": 600,
        "height": 800,
        "ppi": None,
        "grayscale_levels": 16,
        "grayscale": True,
        "direction": ReadingDirection.RIGHT_TO_LEFT,
        "margin_left": 0,
        "margin_top": 0,
        "margin_right": 0,
        "margin_bottom": 0,
        "crop_margins": False,
        "quality": 90,
    }
    values.update(overrides)
    if isinstance(values["direction"], str):
        values["direction"] = ReadingDirection(values["direction"])
    return DeviceProfileSettings(**values)  # type: ignore[arg-type]


def _preferences(root: Path, **overrides: object) -> ApplicationPreferences:
    values: dict[str, object] = {
        "selected_profile_id": BASIC_10_PROFILE_ID,
        "download_concurrency": 2,
        "download_directory": root / "downloads",
        "export_directory": root / "exports",
        "cache_directory": root / "cache",
        "cache_limit_bytes": GIB,
        "cache_retention_days": 30,
    }
    values.update(overrides)
    return ApplicationPreferences(**values)  # type: ignore[arg-type]


def test_factory_profiles_match_documented_generation_frames() -> None:
    assert [(item.name, item.width, item.height, item.ppi) for item in FACTORY_DEVICE_PROFILES] == [
        ("Kindle Básico 8ª geração", 600, 800, 167),
        ("Kindle Básico 10ª geração", 600, 800, 167),
        ("Kindle Paperwhite 10ª geração", 1072, 1448, 300),
    ]
    assert all(item.built_in and item.grayscale_levels == 16 for item in FACTORY_DEVICE_PROFILES)


def test_valid_profile_fixture_round_trips_and_defaults_are_conservative() -> None:
    fixture = json.loads((FIXTURES / "valid_profile.json").read_text(encoding="utf-8"))
    profile = _profile(**fixture)
    preferences = _preferences(Path("C:/settings-test"))

    assert profile.width == 900
    assert profile.height == 1200
    assert profile.direction is ReadingDirection.RIGHT_TO_LEFT
    assert profile.crop_margins is False
    assert preferences.download_concurrency == 2
    assert preferences.cache_limit_bytes == GIB
    assert preferences.cache_retention_days == 30


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "../fora"},
        {"width": 10_001},
        {"width": 10_000, "height": 10_000},
        {"width": 80, "margin_left": 40, "margin_right": 40},
        {"quality": 0},
        {"grayscale": False},
    ],
)
def test_invalid_profile_values_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(DomainValidationError):
        _profile(**overrides)


def test_invalid_profile_fixture_and_resource_preferences_are_rejected() -> None:
    fixture = json.loads((FIXTURES / "invalid_profile.json").read_text(encoding="utf-8"))
    with pytest.raises(DomainValidationError):
        _profile(**fixture)

    root = Path("C:/settings-test")
    with pytest.raises(DomainValidationError):
        _preferences(root, download_concurrency=3)
    with pytest.raises(DomainValidationError):
        _preferences(root, cache_limit_bytes=99 * MIB)
    with pytest.raises(DomainValidationError):
        _preferences(root, cache_retention_days=366)


def test_resource_paths_must_be_absolute_disjoint_and_not_network_paths() -> None:
    root = Path("C:/settings-test")
    with pytest.raises(DomainValidationError):
        _preferences(root, export_directory=root / "downloads" / "exports")
    with pytest.raises(DomainValidationError):
        _preferences(
            root,
            cache_directory=Path("\\\\server\\share\\cache"),
        )

