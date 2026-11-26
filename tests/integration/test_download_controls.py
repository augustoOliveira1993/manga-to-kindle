from __future__ import annotations

import threading
from pathlib import Path

from manga_to_kindle.application.downloads.controls import (
    DownloadControls,
    DownloadControlSignals,
)
from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.queue import DownloadQueue
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from tests.download_support import (
    AuthorizedProvider,
    FakeTransport,
    NeverCancelled,
    make_catalog,
    make_reference,
    make_repository,
)


def test_pause_resume_cancel_are_persisted_and_cancel_starts_no_new_page(
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("control-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    signals = DownloadControlSignals()
    controls = DownloadControls(repository, signals)
    try:
        repository.set_job_state(queued.job.id, DownloadState.RUNNING)
        controls.pause(queued.job.id)
        paused = repository.get(queued.job.id)
        assert paused is not None and paused.job.state is DownloadState.PAUSED
        assert signals.pause_event(queued.job.id).is_set()

        controls.resume(queued.job.id)
        resumed = repository.get(queued.job.id)
        assert resumed is not None and resumed.job.state is DownloadState.RUNNING
        assert not signals.pause_event(queued.job.id).is_set()

        controls.cancel(queued.job.id)
        requested = repository.get(queued.job.id)
        assert requested is not None
        assert requested.job.cancel_requested
        assert signals.cancel_event(queued.job.id).is_set()

        transport = FakeTransport()
        result = DownloadQueue(
            repository,
            transport,
            PageStore(tmp_path / "profile" / "downloads"),
            policy,
            signals,
        ).execute(
            job_id=queued.job.id,
            provider=provider,
            references={(chapter.id, reference.source_id): reference},
            cancellation=NeverCancelled(),
        )
        assert result.state is DownloadState.CANCELLED
        assert transport.calls == []
    finally:
        database.close()


def test_pause_finishes_active_pages_and_resume_skips_completed_pages(tmp_path: Path) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    references = tuple(make_reference(f"pause-page-{index}", index) for index in range(3))
    provider = AuthorizedProvider({chapter.id: references})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    signals = DownloadControlSignals()
    controls = DownloadControls(repository, signals)
    transport = FakeTransport(wait_for_two=True, delay_seconds=0.1)
    queue = DownloadQueue(
        repository,
        transport,
        PageStore(tmp_path / "profile" / "downloads"),
        policy,
        signals,
    )
    repository.set_job_state(queued.job.id, DownloadState.RUNNING)
    results = []
    errors: list[Exception] = []

    def execute_queue() -> None:
        try:
            results.append(
                queue.execute(
                    job_id=queued.job.id,
                    provider=provider,
                    references={(chapter.id, ref.source_id): ref for ref in references},
                    cancellation=NeverCancelled(),
                )
            )
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=execute_queue)
    worker.start()
    assert transport.both_open.wait(2)
    controls.pause(queued.job.id)
    worker.join(5)

    assert not worker.is_alive()
    assert not errors
    assert results[0].state is DownloadState.PAUSED
    paused = repository.get(queued.job.id)
    assert paused is not None
    assert sum(page.state.value == "complete" for page in paused.pages) == 2
    assert len(transport.calls) == 2

    controls.resume(queued.job.id)
    resumed = queue.execute(
        job_id=queued.job.id,
        provider=provider,
        references={(chapter.id, ref.source_id): ref for ref in references},
        cancellation=NeverCancelled(),
    )
    assert resumed.state is DownloadState.SUCCEEDED
    assert resumed.completed_pages == 3
    assert len(transport.calls) == 3
    database.close()


def test_cancel_during_stream_discards_partial_and_does_not_start_next_page(
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    references = tuple(make_reference(f"cancel-page-{index}", index) for index in range(2))
    provider = AuthorizedProvider({chapter.id: references})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    signals = DownloadControlSignals()
    controls = DownloadControls(repository, signals)
    transport = FakeTransport(delay_seconds=0.2)
    store = PageStore(tmp_path / "profile" / "downloads")
    queue = DownloadQueue(repository, transport, store, policy, signals)
    repository.set_job_state(queued.job.id, DownloadState.RUNNING)
    results = []
    errors: list[Exception] = []

    def execute_queue() -> None:
        try:
            results.append(
                queue.execute(
                    job_id=queued.job.id,
                    provider=provider,
                    references={(chapter.id, ref.source_id): ref for ref in references},
                    cancellation=NeverCancelled(),
                    user_parallelism=1,
                )
            )
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=execute_queue)
    worker.start()
    assert transport.opened.wait(2)
    controls.cancel(queued.job.id)
    worker.join(5)

    assert not worker.is_alive()
    assert not errors
    assert results[0].state is DownloadState.CANCELLED
    assert len(transport.calls) == 1
    current = repository.get(queued.job.id)
    assert current is not None
    assert not any(page.state.value == "complete" for page in current.pages)
    assert not list((tmp_path / "profile" / "downloads" / "staging").rglob("*.part"))
    database.close()
