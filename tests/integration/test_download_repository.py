from __future__ import annotations

from pathlib import Path

import pytest

from manga_to_kindle.application.downloads.enqueue import EnqueueDownload
from manga_to_kindle.application.downloads.errors import DuplicateActiveDownload
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository
from tests.download_support import AuthorizedProvider, make_catalog, make_reference, make_repository


def test_download_queue_and_page_identity_survive_database_reopen(tmp_path: Path) -> None:
    catalog = make_catalog()
    chapter = catalog.chapters[0]
    references = (make_reference("persist-1", 0), make_reference("persist-2", 1))
    provider = AuthorizedProvider({chapter.id: references})
    database, repository = make_repository(tmp_path, catalog)
    root = tmp_path / "profile" / "downloads"
    policy = ExternalUrlPolicy(lambda _host: ("93.184.216.34",))
    queued = EnqueueDownload(repository, policy).execute(
        provider=provider,
        catalog=catalog,
        selected_chapter_ids=(chapter.id,),
    )
    database_path = database.database_path
    database.close()

    reopened = SQLiteDatabase(database_path)
    reopened.initialize()
    reopened_repository = DownloadRepository(reopened, root)
    try:
        restored = reopened_repository.get(queued.job.id)
        assert restored is not None
        assert restored.job.state is DownloadState.QUEUED
        assert restored.job.total == 2
        assert [(page.source_page_id, page.position) for page in restored.pages] == [
            ("persist-1", 0),
            ("persist-2", 1),
        ]
        with pytest.raises(DuplicateActiveDownload):
            reopened_repository.enqueue(
                manga_id=catalog.manga.id,
                provider_id=provider.provider_id,
                chapter_pages=((chapter, references),),
                policy_snapshot={"provider_id": provider.provider_id},
            )
        assert len(reopened_repository.list_jobs()) == 1
    finally:
        reopened.close()
