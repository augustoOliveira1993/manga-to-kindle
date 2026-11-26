from __future__ import annotations

from pathlib import Path

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.recovery import DownloadRecovery
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.downloads import DownloadPageState
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.download_repository import (
    DownloadQueueSnapshot,
    DownloadRepository,
)
from tests.download_support import (
    VALID_PNG,
    AuthorizedProvider,
    NeverCancelled,
    make_catalog,
    make_reference,
    make_repository,
)


def _queue_one_page(
    tmp_path: Path,
) -> tuple[SQLiteDatabase, DownloadRepository, PageStore, DownloadQueueSnapshot]:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("recoverable-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    snapshot = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    store = PageStore(tmp_path / "profile" / "downloads")
    return database, repository, store, snapshot


def test_recovery_removes_only_known_partial_and_requires_explicit_resume(
    tmp_path: Path,
) -> None:
    database, repository, store, queued = _queue_one_page(tmp_path)
    page = queued.pages[0]
    try:
        repository.set_job_state(queued.job.id, DownloadState.RUNNING)
        repository.begin_page_attempt(queued.job.id, page.id)
        partial = store.temporary_path_for(queued.job.id, page.id)
        partial.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(b"partial response")
        repository.set_page_temporary_path(queued.job.id, page.id, partial)

        summary = DownloadRecovery(repository, store).execute()

        current = repository.get(queued.job.id)
        assert current is not None
        assert current.job.state is DownloadState.INTERRUPTED
        assert current.pages[0].state is DownloadPageState.INTERRUPTED
        assert summary.interrupted_jobs == 1
        assert summary.partial_files_removed == 1
        assert not partial.exists()
        assert not current.job.cancel_requested
    finally:
        database.close()


def test_recovery_finishes_database_commit_after_atomic_file_promotion(
    tmp_path: Path,
) -> None:
    database, repository, store, queued = _queue_one_page(tmp_path)
    page = queued.pages[0]
    original = VALID_PNG.read_bytes()
    try:
        repository.set_job_state(queued.job.id, DownloadState.RUNNING)
        repository.begin_page_attempt(queued.job.id, page.id)
        temporary = store.temporary_path_for(queued.job.id, page.id)
        repository.set_page_temporary_path(queued.job.id, page.id, temporary)
        artifact = store.stage_chunks(
            job_id=queued.job.id,
            page_id=page.id,
            chapter_id=page.chapter_id,
            chunks=(original,),
            content_type="image/png",
            cancellation=NeverCancelled(),
        )
        repository.mark_page_staging(
            queued.job.id,
            page.id,
            temporary_path=artifact.temporary_path,
            final_path=artifact.final_path,
            byte_size=artifact.image.byte_size,
            sha256=artifact.image.sha256,
        )
        final = store.promote(artifact, job_id=queued.job.id, page_id=page.id)

        summary = DownloadRecovery(repository, store).execute()
        current = repository.get(queued.job.id)

        assert summary.completed_pages_recovered == 1
        assert current is not None
        assert current.job.state is DownloadState.SUCCEEDED
        assert current.pages[0].state is DownloadPageState.COMPLETE
        assert current.pages[0].original_path == final
        assert final.read_bytes() == original
    finally:
        database.close()
