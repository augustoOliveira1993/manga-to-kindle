from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer
from tests.image_support import FIXTURES, make_image_stack

from manga_to_kindle.presentation.qt.views.image_import_view import ImageImportView
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner


def test_selected_page_shows_preview_from_background_worker(qt_core_app, tmp_path) -> None:
    database, _root, _store, _repository, _reader, _decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")
    runner = OperationRunner()
    view = ImageImportView(runner)
    view._importer = importer
    loop = QEventLoop()
    runner.succeeded.connect(
        lambda operation_id, _result: loop.quit()
        if operation_id == view._preview_id
        else None
    )
    view._populate_plan(plan)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(3000, idle_loop.quit)
        idle_loop.exec()

    pixmap = view.preview_image.pixmap()
    assert pixmap is not None and not pixmap.isNull()
    assert pixmap.width() <= 150 and pixmap.height() <= 200
    database.close()
