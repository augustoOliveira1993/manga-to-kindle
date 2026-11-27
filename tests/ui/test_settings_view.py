from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from manga_to_kindle.application.settings.cache import (
    ClearRegenerableCache,
    PreviewCacheCleanup,
)
from manga_to_kindle.application.settings.device_profiles import (
    ListDeviceProfiles,
    RemoveDeviceProfile,
    SaveDeviceProfile,
)
from manga_to_kindle.application.settings.preferences import (
    GetApplicationPreferences,
    ResetPreferences,
    SaveApplicationPreferences,
)
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.domain.settings import PAPERWHITE_10_PROFILE_ID
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.settings_repository import SettingsRepository
from manga_to_kindle.presentation.qt.views.settings_view import SettingsView
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


def _wait(runner: OperationRunner, operation_id: str, qt_core_app) -> None:
    loop = QEventLoop()
    runner.finished.connect(lambda finished: loop.quit() if finished == operation_id else None)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(5000, idle_loop.quit)
        idle_loop.exec()
        runner.idle.disconnect(idle_loop.quit)


def test_settings_view_loads_factory_profiles_and_saves_selected_profile(
    qt_core_app,
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = AppPaths.from_root(tmp_path / "profile")
    paths.ensure()
    database = SQLiteDatabase(paths.database_file)
    database.initialize()
    repository = SettingsRepository(database)
    runner = OperationRunner()
    view = SettingsView(runner)
    view.bind_services(
        GetApplicationPreferences(repository, paths),
        ListDeviceProfiles(repository),
        SaveDeviceProfile(repository),
        RemoveDeviceProfile(repository, repository),
        SaveApplicationPreferences(repository, profile_lookup=repository),
        ResetPreferences(repository, paths),
        PreviewCacheCleanup(repository),
        ClearRegenerableCache(repository),
    )
    load_id = next(iter(view._operation_kinds))
    _wait(runner, load_id, qt_core_app)

    paperwhite_index = view.profile_combo.findData(PAPERWHITE_10_PROFILE_ID)
    assert paperwhite_index >= 0, (
        view.status_label.text(), view.profile_combo.count(), view._operation_kinds
    )
    view.profile_combo.setCurrentIndex(paperwhite_index)
    assert view.width_spin.value() == 1072
    assert view.height_spin.value() == 1448
    assert not view.width_spin.isEnabled()
    assert view.save_profile_button.isEnabled()
    view.concurrency_spin.setValue(1)
    QTest.mouseClick(view.save_profile_button, Qt.MouseButton.LeftButton)
    save_id = next(iter(view._operation_kinds))
    _wait(runner, save_id, qt_core_app)

    saved = repository.get_preferences()
    assert saved is not None
    assert saved.selected_profile_id == PAPERWHITE_10_PROFILE_ID
    assert saved.download_concurrency == 1
    assert len(repository.list_custom_profiles()) == 0

    custom_profile = SaveDeviceProfile(repository).duplicate(
        PAPERWHITE_10_PROFILE_ID,
        "Meu Paperwhite",
    )
    view.dark_button.setChecked(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )
    view._confirm_restore()
    assert repository.get_preferences() == saved
    assert view.dark_button.isChecked()

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    view._confirm_restore()
    reset_id = next(iter(view._operation_kinds))
    _wait(runner, reset_id, qt_core_app)
    reset_preferences = repository.get_preferences()
    assert reset_preferences is not None
    assert reset_preferences.selected_profile_id != custom_profile.id
    assert reset_preferences.download_concurrency == 2
    assert repository.list_custom_profiles() == (custom_profile,)
    assert view.light_button.isChecked()

    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *_args, **_kwargs: ("Meu leitor editável", True),
    )
    QTest.mouseClick(view.duplicate_profile_button, Qt.MouseButton.LeftButton)
    duplicate_id = next(iter(view._operation_kinds))
    _wait(runner, duplicate_id, qt_core_app)
    edited_id = view.profile_combo.currentData()
    view.width_spin.setValue(1000)
    view.height_spin.setValue(1400)
    view.direction_combo.setCurrentIndex(
        view.direction_combo.findData(ReadingDirection.LEFT_TO_RIGHT)
    )
    QTest.mouseClick(view.save_profile_button, Qt.MouseButton.LeftButton)
    _wait(runner, next(iter(view._operation_kinds)), qt_core_app)

    edited = next(
        profile for profile in repository.list_custom_profiles() if profile.id == edited_id
    )
    assert (edited.width, edited.height) == (1000, 1400)
    assert edited.direction is ReadingDirection.LEFT_TO_RIGHT
    final_preferences = repository.get_preferences()
    assert final_preferences is not None
    assert final_preferences.selected_profile_id == edited_id
    database.close()
