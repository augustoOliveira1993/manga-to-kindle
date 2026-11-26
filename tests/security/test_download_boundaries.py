from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.download_support import (
    AuthorizedProvider,
    FakeTransport,
    NeverCancelled,
    make_catalog,
    make_reference,
    make_repository,
)

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.errors import DownloadUnavailable
from manga_to_kindle.application.downloads.queue import DownloadQueue
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


def test_runtime_rechecks_capability_before_transport_even_if_record_exists(
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("blocked-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    provider.capabilities = replace(
        provider.capabilities,
        download_authorized=False,
        authorization_evidence=None,
        authorization_reviewed_on=None,
        authorization_scope=None,
    )
    transport = FakeTransport()
    try:
        with pytest.raises(DownloadUnavailable):
            DownloadQueue(
                repository,
                transport,
                PageStore(tmp_path / "profile" / "downloads"),
                policy,
            ).execute(
                job_id=queued.job.id,
                provider=provider,
                references={(chapter.id, reference.source_id): reference},
                cancellation=NeverCancelled(),
            )
        assert transport.calls == []
        assert repository.list_jobs()[0].state is DownloadState.QUEUED
    finally:
        database.close()


def test_transport_peer_must_match_the_address_validated_by_url_policy(tmp_path: Path) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("peer-check-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    transport = FakeTransport(connected_address="127.0.0.1")
    try:
        result = DownloadQueue(
            repository,
            transport,
            PageStore(tmp_path / "profile" / "downloads"),
            policy,
        ).execute(
            job_id=queued.job.id,
            provider=provider,
            references={(chapter.id, reference.source_id): reference},
            cancellation=NeverCancelled(),
        )
        snapshot = repository.get(queued.job.id)

        assert result.state is DownloadState.FAILED
        assert len(transport.calls) == 1
        assert snapshot is not None
        assert snapshot.pages[0].state.value == "failed"
        assert snapshot.pages[0].original_path is None
    finally:
        database.close()


@pytest.mark.parametrize(
    ("status", "headers"),
    (
        (403, {}),
        (302, {"location": "https://unapproved.example.test/redirect"}),
        (200, {"content-type": "text/html"}),
        (200, {"content-type": "image/png", "content-length": "1"}),
    ),
)
def test_restricted_redirect_and_invalid_mime_fail_without_retry_or_followup(
    tmp_path: Path,
    status: int,
    headers: dict[str, str],
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    reference = make_reference("restricted-page", 0)
    provider = AuthorizedProvider({chapter.id: (reference,)})
    database, repository = make_repository(tmp_path, catalog)
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    transport = FakeTransport(statuses=(status,), headers=headers)
    try:
        result = DownloadQueue(
            repository,
            transport,
            PageStore(tmp_path / "profile" / "downloads"),
            policy,
        ).execute(
            job_id=queued.job.id,
            provider=provider,
            references={(chapter.id, reference.source_id): reference},
            cancellation=NeverCancelled(),
        )

        assert result.state is DownloadState.FAILED
        assert len(transport.calls) == 1
        assert transport.calls[0][0].destination.host == "pages.example.test"
    finally:
        database.close()
