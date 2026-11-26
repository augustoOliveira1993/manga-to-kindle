from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.queue import DownloadQueue, DownloadRunResult
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.presentation.qt.workers.adapter import OperationRunner
from manga_to_kindle.presentation.qt.workers.download_worker import make_download_operation
from tests.download_support import (
    AuthorizedProvider,
    FakeTransport,
    make_catalog,
    make_reference,
    make_repository,
)


def test_download_worker_emits_progress_from_background_thread_and_keeps_ui_responsive(
    qt_core_app: QApplication,
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("worker-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    transport = FakeTransport(delay_seconds=0.05)
    queue = DownloadQueue(
        repository,
        transport,
        PageStore(tmp_path / "profile" / "downloads"),
        policy,
    )
    runner = OperationRunner()
    loop = QEventLoop()
    result_values: list[object] = []
    errors: list[str] = []
    progress: list[tuple[int, object, str]] = []
    timer_fired: list[bool] = []
    runner.succeeded.connect(lambda _operation_id, result: result_values.append(result))
    runner.failed.connect(lambda _operation_id, code: errors.append(code))
    runner.progress.connect(
        lambda _operation_id, done, total, stage: progress.append((done, total, stage))
    )
    runner.finished.connect(lambda _operation_id: QTimer.singleShot(50, loop.quit))
    operation = make_download_operation(
        queue,
        job_id=queued.job.id,
        provider=provider,
        references={(chapter.id, reference.source_id): reference},
    )
    try:
        main_thread = threading.get_ident()
        runner.start(operation)
        QTimer.singleShot(10, lambda: timer_fired.append(True))
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        qt_core_app.processEvents()

        assert not errors
        assert result_values
        assert timer_fired == [True]
        assert transport.open_thread_ids
        assert transport.open_thread_ids[0] != main_thread
        assert isinstance(result_values[-1], DownloadRunResult)
        assert result_values[-1].completed_pages == 1
        assert progress and progress[-1][0:2] == (1, 1), (result_values, progress)
    finally:
        runner.cancel_all()
        if runner.active_count:
            qt_core_app.processEvents()
        database.close()
