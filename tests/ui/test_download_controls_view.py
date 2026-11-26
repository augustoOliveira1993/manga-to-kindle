from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from tests.download_support import (
    AuthorizedProvider,
    make_catalog,
    make_reference,
    make_repository,
)

from manga_to_kindle.application.downloads.controls import (
    DownloadControls,
    DownloadControlSignals,
)
from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


def _wait_for(qt_core_app, predicate) -> None:
    for _ in range(150):
        qt_core_app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("A operação da fila não terminou no prazo esperado.")


def test_downloads_view_reads_persisted_jobs_and_enables_only_safe_controls(
    main_window,
    qt_core_app,
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("ui-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    repository.set_job_state(queued.job.id, DownloadState.RUNNING)
    signals = DownloadControlSignals()
    view = main_window.downloads_view
    try:
        view.bind_queue(repository, DownloadControls(repository, signals))
        _wait_for(
            qt_core_app,
            lambda: view.job_list.count() == 1 and view._operation_id is None,
        )
        view.job_list.setCurrentRow(0)

        assert "0/1 páginas" in view.chapter_progress.text()
        assert view.page_list.count() == 1
        assert "Página 1: Na fila" in view.page_list.item(0).text()
        assert view.pause_button.isEnabled()
        assert not view.resume_button.isEnabled()
        assert view.cancel_button.isEnabled()
        QTest.mouseClick(view.pause_button, Qt.MouseButton.LeftButton)
        _wait_for(qt_core_app, lambda: "Pausado" in view.job_list.item(0).text())

        snapshot = repository.get(queued.job.id)
        assert snapshot is not None and snapshot.job.state is DownloadState.PAUSED
        assert signals.pause_event(queued.job.id).is_set()
        assert not view.resume_button.isEnabled()
    finally:
        database.close()
