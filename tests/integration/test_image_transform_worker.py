from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from sqlalchemy import func, select

from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.domain.image_processing import ImageProcessingProfile, ImageTransformOptions
from manga_to_kindle.infrastructure.persistence.models import ImageImportJobRecord, PageRecord
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner
from manga_to_kindle.presentation.qt.workers.image_worker import make_image_import_operation
from tests.image_support import FIXTURES, make_image_stack, make_new_target


class DelayedReader:
    def __init__(self, reader, *, delay: float) -> None:
        self._reader = reader
        self.delay = delay
        self.thread_ids: list[int] = []

    def enumerate(self, source_path: Path):
        return self._reader.enumerate(source_path)

    def read(self, source_path, source_file, limit):
        self.thread_ids.append(threading.get_ident())
        time.sleep(self.delay)
        return self._reader.read(source_path, source_file, limit)


def test_image_import_runs_off_ui_thread_and_keeps_event_loop_responsive(
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    database, _root, store, repository, reader, decoder, _importer = make_image_stack(tmp_path)
    delayed = DelayedReader(reader, delay=0.05)
    importer = ImportImages(reader, decoder, store, repository)
    plan = importer.preview_source(FIXTURES / "valid")
    importer = ImportImages(delayed, decoder, store, repository)
    runner = OperationRunner()
    loop = QEventLoop()
    results: list[object] = []
    errors: list[str] = []
    timer_fired: list[bool] = []
    runner.succeeded.connect(lambda _operation_id, result: (results.append(result), loop.quit()))
    runner.failed.connect(lambda _operation_id, code: (errors.append(code), loop.quit()))
    operation = make_image_import_operation(
        importer,
        plan,
        make_new_target(),
        ordered_paths=tuple(image.relative_path for image in plan.images),
        profile=ImageProcessingProfile(),
        options=ImageTransformOptions(),
        confirmed_authorization=True,
    )
    main_thread = threading.get_ident()
    runner.start(operation)
    QTimer.singleShot(10, lambda: timer_fired.append(True))
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(3000, idle_loop.quit)
        idle_loop.exec()

    assert not errors
    assert results
    assert timer_fired == [True]
    assert delayed.thread_ids
    assert all(thread_id != main_thread for thread_id in delayed.thread_ids)
    database.close()


def test_cancel_during_import_discards_staged_files_and_database_rows(
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    source = tmp_path / "one-page"
    source.mkdir()
    (source / "pagina.png").write_bytes((FIXTURES / "valid" / "pagina_1.png").read_bytes())
    database, image_root, store, repository, reader, decoder, _importer = make_image_stack(tmp_path)
    plan = ImportImages(reader, decoder, store, repository).preview_source(source)
    delayed = DelayedReader(reader, delay=0.08)
    importer = ImportImages(delayed, decoder, store, repository)
    runner = OperationRunner()
    loop = QEventLoop()
    errors: list[str] = []
    runner.failed.connect(lambda _operation_id, code: (errors.append(code), loop.quit()))
    operation_id = runner.start(
        make_image_import_operation(
            importer,
            plan,
            make_new_target(),
            ordered_paths=(plan.images[0].relative_path,),
            profile=ImageProcessingProfile(),
            options=ImageTransformOptions(),
            confirmed_authorization=True,
        )
    )
    QTimer.singleShot(10, lambda: runner.cancel(operation_id))
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    qt_core_app.processEvents()
    if runner.active_count:
        idle_loop = QEventLoop()
        runner.idle.connect(idle_loop.quit)
        QTimer.singleShot(3000, idle_loop.quit)
        idle_loop.exec()

    assert errors == ["IMAGE_IMPORT_CANCELLED"]
    with database.unit_of_work() as session:
        assert session.scalar(select(func.count()).select_from(PageRecord)) == 0
        job_id = next(iter(session.scalars(select(ImageImportJobRecord.id))))
        job = session.get(ImageImportJobRecord, job_id)
    assert job is not None and job.state == "cancelled"
    assert not list((image_root / ".staging").glob("*"))
    assert not list((image_root / "imports").glob("*"))
    database.close()
