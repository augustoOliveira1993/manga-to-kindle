from __future__ import annotations

from PySide6.QtCore import QEventLoop, Qt, QTimer
from tests.image_support import FIXTURES, make_image_stack

from manga_to_kindle.presentation.qt.views.image_import_view import ImageImportView
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


def test_view_requires_plan_authorization_and_explicit_target(qt_core_app, tmp_path) -> None:
    database, _root, _store, _repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    runner = OperationRunner()
    view = ImageImportView(runner)
    plan = importer.preview_source(FIXTURES / "valid")
    view._importer = importer
    loop = QEventLoop()
    runner.succeeded.connect(
        lambda operation_id, _result: loop.quit()
        if operation_id == view._preview_id
        else None
    )
    view._populate_plan(plan)
    view.manga_title_input.setText("Demo")
    view.chapter_title_input.setText("Chapter 1")
    view.authorization_checkbox.setChecked(False)
    view._update_import_enabled()

    assert view.authorization_checkbox.isChecked() is False
    assert view.cancel_button.isEnabled() is False
    assert view.crop_checkbox.isChecked() is False
    assert view.split_checkbox.isChecked() is False
    assert all(spin.value() == 0 for spin in view.margin_spins)
    assert view.import_button.isEnabled() is False

    view.authorization_checkbox.setChecked(True)
    assert view.import_button.isEnabled() is True
    view.authorization_checkbox.setChecked(False)
    assert view.import_button.isEnabled() is False
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(3000, idle_loop.quit)
        idle_loop.exec()
    database.close()


def test_preview_list_can_be_reordered_manually(qt_core_app, tmp_path) -> None:
    database, _root, _store, _repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")
    view = ImageImportView(OperationRunner())
    view._populate_plan(plan)

    view._move_selected(1)

    assert [
        view.image_list.item(row).data(Qt.ItemDataRole.UserRole)
        for row in range(view.image_list.count())
    ] == [
        "pagina_2.jpg",
        "pagina_1.png",
        "pagina_10.webp",
    ]
    database.close()
