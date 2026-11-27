"""Persist application preferences and user profiles in the shared SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from manga_to_kindle.application.settings.cache import CacheCategory, CacheManifestItem
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.settings import ApplicationPreferences, DeviceProfileSettings
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import (
    ApplicationPreferencesRecord,
    CacheManifestRecord,
    DeviceProfileRecord,
)


class SettingsPersistenceError(RuntimeError):
    code = "SETTINGS_PERSISTENCE_FAILED"


class SettingsRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def get_preferences(self) -> ApplicationPreferences | None:
        with self._database.unit_of_work() as session:
            record = session.get(ApplicationPreferencesRecord, 1)
            return _preferences_from_record(record) if record is not None else None

    def save_preferences(self, preferences: ApplicationPreferences) -> None:
        if (
            preferences.download_directory is None
            or preferences.export_directory is None
            or preferences.cache_directory is None
        ):
            raise SettingsPersistenceError("As três pastas padrão precisam estar definidas.")
        with self._database.unit_of_work() as session:
            record = session.get(ApplicationPreferencesRecord, 1)
            if record is None:
                record = ApplicationPreferencesRecord(id=1)
                session.add(record)
            record.selected_profile_id = preferences.selected_profile_id
            record.download_concurrency = preferences.download_concurrency
            record.download_directory = str(preferences.download_directory)
            record.export_directory = str(preferences.export_directory)
            record.cache_directory = str(preferences.cache_directory)
            record.cache_limit_bytes = preferences.cache_limit_bytes
            record.cache_retention_days = preferences.cache_retention_days
            record.updated_at = datetime.now(UTC)

    def list_custom_profiles(self) -> tuple[DeviceProfileSettings, ...]:
        with self._database.unit_of_work() as session:
            records = tuple(
                session.scalars(select(DeviceProfileRecord).order_by(func.lower(DeviceProfileRecord.name)))
            )
            return tuple(_profile_from_record(record) for record in records)

    def save_custom_profile(self, profile: DeviceProfileSettings) -> None:
        if profile.built_in:
            raise SettingsPersistenceError("Perfis de fábrica são somente leitura.")
        with self._database.unit_of_work() as session:
            existing_names = tuple(
                session.execute(
                    select(DeviceProfileRecord.id, DeviceProfileRecord.name).where(
                        DeviceProfileRecord.id != profile.id
                    )
                )
            )
            if any(name.casefold() == profile.name.casefold() for _, name in existing_names):
                raise SettingsPersistenceError("Já existe um perfil com esse nome.")
            record = session.get(DeviceProfileRecord, profile.id)
            if record is None:
                record = DeviceProfileRecord(id=profile.id, name=profile.name)
                session.add(record)
            record.name = profile.name
            record.preferences = _profile_payload(profile)
            record.updated_at = datetime.now(UTC)

    def delete_custom_profile(self, profile_id: UUID) -> bool:
        with self._database.unit_of_work() as session:
            record = session.get(DeviceProfileRecord, profile_id)
            if record is None:
                return False
            session.delete(record)
            return True

    def list_cache_items(self, root_path: Path) -> tuple[CacheManifestItem, ...]:
        root = str(root_path.resolve(strict=False))
        with self._database.unit_of_work() as session:
            records = tuple(
                session.scalars(
                    select(CacheManifestRecord)
                    .where(CacheManifestRecord.root_path == root)
                    .order_by(CacheManifestRecord.last_accessed_at)
                )
            )
            return tuple(
                CacheManifestItem(
                    id=record.id,
                    root_path=Path(record.root_path),
                    relative_path=Path(record.relative_path),
                    sha256=record.sha256,
                    size_bytes=record.size_bytes,
                    last_accessed_at=_utc(record.last_accessed_at),
                    category=CacheCategory(record.category),
                    in_use=record.in_use,
                )
                for record in records
            )

    def register_cache_item(self, item: CacheManifestItem) -> None:
        with self._database.unit_of_work() as session:
            record = session.scalar(
                select(CacheManifestRecord).where(
                    CacheManifestRecord.root_path == str(item.root_path),
                    CacheManifestRecord.relative_path == item.relative_path.as_posix(),
                )
            )
            if record is None:
                record = CacheManifestRecord(
                    id=item.id,
                    root_path=str(item.root_path),
                    relative_path=item.relative_path.as_posix(),
                    sha256=item.sha256,
                    size_bytes=item.size_bytes,
                    last_accessed_at=item.last_accessed_at,
                    category=item.category.value,
                    in_use=item.in_use,
                )
                session.add(record)
            else:
                record.sha256 = item.sha256
                record.size_bytes = item.size_bytes
                record.last_accessed_at = item.last_accessed_at
                record.category = item.category.value
                record.in_use = item.in_use

    def delete_cache_item(self, item_id: UUID) -> None:
        with self._database.unit_of_work() as session:
            record = session.get(CacheManifestRecord, item_id)
            if record is not None:
                session.delete(record)


def _preferences_from_record(record: ApplicationPreferencesRecord) -> ApplicationPreferences:
    try:
        return ApplicationPreferences(
            selected_profile_id=record.selected_profile_id,
            download_concurrency=record.download_concurrency,
            download_directory=Path(record.download_directory),
            export_directory=Path(record.export_directory),
            cache_directory=Path(record.cache_directory),
            cache_limit_bytes=record.cache_limit_bytes,
            cache_retention_days=record.cache_retention_days,
        )
    except (TypeError, ValueError):
        raise SettingsPersistenceError("As preferências locais precisam ser revisadas.") from None


def _profile_payload(profile: DeviceProfileSettings) -> dict[str, object]:
    return {
        "model": profile.model,
        "generation": profile.generation,
        "width": profile.width,
        "height": profile.height,
        "ppi": profile.ppi,
        "grayscale_levels": profile.grayscale_levels,
        "grayscale": profile.grayscale,
        "direction": profile.direction.value,
        "margin_left": profile.margin_left,
        "margin_top": profile.margin_top,
        "margin_right": profile.margin_right,
        "margin_bottom": profile.margin_bottom,
        "crop_margins": profile.crop_margins,
        "quality": profile.quality,
    }


def _profile_from_record(record: DeviceProfileRecord) -> DeviceProfileSettings:
    preferences = record.preferences
    try:
        return DeviceProfileSettings(
            id=record.id,
            name=record.name,
            model=_stored_text(preferences.get("model", "Perfil personalizado")),
            generation=_optional_int(preferences.get("generation")),
            width=_stored_int(preferences.get("width", 600)),
            height=_stored_int(preferences.get("height", 800)),
            ppi=_optional_int(preferences.get("ppi")),
            grayscale_levels=_stored_int(preferences.get("grayscale_levels", 16)),
            grayscale=_stored_bool(preferences.get("grayscale", True)),
            direction=ReadingDirection(_stored_text(preferences.get("direction", "rtl"))),
            margin_left=_stored_int(preferences.get("margin_left", 0)),
            margin_top=_stored_int(preferences.get("margin_top", 0)),
            margin_right=_stored_int(preferences.get("margin_right", 0)),
            margin_bottom=_stored_int(preferences.get("margin_bottom", 0)),
            crop_margins=_stored_bool(preferences.get("crop_margins", False)),
            quality=_stored_int(preferences.get("quality", 90)),
            built_in=False,
        )
    except (KeyError, TypeError, ValueError):
        raise SettingsPersistenceError(
            "Um perfil salvo está inválido e foi mantido para revisão."
        ) from None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise ValueError("invalid integer")
    return value


def _stored_int(value: object) -> int:
    if type(value) is not int:
        raise ValueError("invalid integer")
    return value


def _stored_bool(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("invalid boolean")
    return value


def _stored_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid text")
    return value


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
