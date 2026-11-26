from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.download_support import (
    AuthorizedProvider,
    make_catalog,
    make_reference,
    make_repository,
)

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.errors import (
    DownloadUnavailable,
    DuplicateActiveDownload,
)
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy


def test_enqueue_persists_selected_pages_in_canonical_order_and_deduplicates_active_job(
    tmp_path: Path,
) -> None:
    catalog = make_catalog(chapter_count=2)
    chapter_one, chapter_two = catalog.chapters
    references = {
        chapter_one.id: (make_reference("page-b", 1), make_reference("page-a", 0)),
        chapter_two.id: (make_reference("page-c", 0),),
    }
    provider = AuthorizedProvider(references)
    database, repository = make_repository(tmp_path, catalog)
    enqueue = EnqueueDownload(
        repository,
        ExternalUrlPolicy(lambda _host: ("93.184.216.34",)),
    )
    try:
        snapshot = enqueue.execute(
            provider=provider,
            catalog=catalog,
            selected_chapter_ids=(chapter_two.id, chapter_one.id),
        )

        assert snapshot.job.provider_id == provider.provider_id
        assert snapshot.chapter_ids == (chapter_one.id, chapter_two.id)
        assert [page.source_page_id for page in snapshot.pages] == [
            "page-a",
            "page-b",
            "page-c",
        ]
        assert [page.position for page in snapshot.pages] == [0, 1, 0]
        assert snapshot.job.total == 3
        with pytest.raises(DuplicateActiveDownload):
            enqueue.execute(
                provider=provider,
                catalog=catalog,
                selected_chapter_ids=(chapter_one.id, chapter_two.id),
            )
        assert len(repository.list_jobs()) == 1
    finally:
        database.close()


def test_unauthorized_provider_is_rejected_before_page_lookup_or_connection(
    tmp_path: Path,
) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    provider = AuthorizedProvider({chapter.id: (make_reference("page-a", 0),)})
    provider.capabilities = replace(
        provider.capabilities,
        download_authorized=False,
        authorization_evidence=None,
        authorization_reviewed_on=None,
        authorization_scope=None,
    )
    database, repository = make_repository(tmp_path, catalog)
    enqueue = EnqueueDownload(repository, ExternalUrlPolicy(None))
    try:
        with pytest.raises(DownloadUnavailable):
            enqueue.execute(
                provider=provider,
                catalog=catalog,
                selected_chapter_ids=(chapter.id,),
            )
        assert provider.get_pages_calls == 0
        assert repository.list_jobs() == ()
    finally:
        database.close()


def test_unapproved_destination_is_rejected_without_persisting_job(tmp_path: Path) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    wrong_host = make_reference("page-a", 0, host="other.example.test")
    provider = AuthorizedProvider({chapter.id: (wrong_host,)})
    database, repository = make_repository(tmp_path, catalog)
    enqueue = EnqueueDownload(
        repository,
        ExternalUrlPolicy(lambda _host: ("93.184.216.34",)),
    )
    try:
        with pytest.raises(DownloadUnavailable):
            enqueue.execute(
                provider=provider,
                catalog=catalog,
                selected_chapter_ids=(chapter.id,),
            )
        assert repository.list_jobs() == ()
    finally:
        database.close()
