from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.queue import (
    CONNECT_TIMEOUT_SECONDS,
    MAX_GLOBAL_TRANSFERS,
    READ_TIMEOUT_SECONDS,
    DownloadQueue,
)
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.downloads import DownloadPageState
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.persistence.models import PageRecord
from tests.download_support import (
    VALID_PNG,
    AuthorizedProvider,
    FakeTransport,
    NeverCancelled,
    make_catalog,
    make_reference,
    make_repository,
)


def test_authorized_fixture_transport_persists_original_pages_in_catalog_order(
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    references = tuple(make_reference(f"page-{position}", position) for position in range(4))
    provider = AuthorizedProvider({chapter.id: tuple(reversed(references))})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    enqueue = EnqueueDownload(repository, policy)
    queued = enqueue.execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    transport = FakeTransport(wait_for_two=True)
    queue = DownloadQueue(
        repository,
        transport,
        PageStore(tmp_path / "profile" / "downloads"),
        policy,
    )
    reference_map = {
        (chapter.id, reference.source_id): reference for reference in references
    }
    reports: list[tuple[int, int | None, str]] = []
    try:
        result = queue.execute(
            job_id=queued.job.id,
            provider=provider,
            references=reference_map,
            cancellation=NeverCancelled(),
            report_progress=lambda completed, total, stage: reports.append(
                (completed, total, stage)
            ),
        )

        snapshot = repository.get(queued.job.id)
        assert snapshot is not None
        assert result.state is DownloadState.SUCCEEDED, (
            result,
            [(page.source_page_id, page.state, page.error_code) for page in snapshot.pages],
        )
        assert result.completed_pages == 4
        assert snapshot.job.progress == 4
        assert [page.position for page in snapshot.pages] == [0, 1, 2, 3]
        assert all(page.state is DownloadPageState.COMPLETE for page in snapshot.pages)
        assert sum(page.duplicate_content for page in snapshot.pages) == 3
        assert all(page.original_path is not None for page in snapshot.pages)
        assert all(
            page.original_path.read_bytes() == VALID_PNG.read_bytes()
            for page in snapshot.pages
            if page.original_path is not None
        )
        assert transport.max_active == MAX_GLOBAL_TRANSFERS
        assert all(
            connect == CONNECT_TIMEOUT_SECONDS and read == READ_TIMEOUT_SECONDS
            for _, connect, read in transport.calls
        )
        assert {reference.source_id for reference, _, _ in transport.calls} == {
            reference.source_id for reference in references
        }
        assert reports[-1][0:2] == (4, 4)
        with database.unit_of_work() as session:
            local_pages = tuple(
                session.scalars(
                    select(PageRecord).where(PageRecord.chapter_id == chapter.id)
                )
            )
        assert len(local_pages) == 4
        assert len({page.position for page in local_pages}) == 4
    finally:
        database.close()


def test_retry_response_is_retried_without_exceeding_attempt_limit(tmp_path: Path) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("retry-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    transport = FakeTransport(statuses=(429, 200), headers={"retry-after": "0"})
    queue = DownloadQueue(
        repository,
        transport,
        PageStore(tmp_path / "profile" / "downloads"),
        policy,
    )
    try:
        result = queue.execute(
            job_id=queued.job.id,
            provider=provider,
            references={(chapter.id, reference.source_id): reference},
            cancellation=NeverCancelled(),
        )

        snapshot = repository.get(queued.job.id)
        assert snapshot is not None
        assert result.state is DownloadState.SUCCEEDED
        assert len(transport.calls) == 2
        assert snapshot.pages[0].attempts == 2
        assert snapshot.pages[0].state is DownloadPageState.COMPLETE
    finally:
        database.close()
