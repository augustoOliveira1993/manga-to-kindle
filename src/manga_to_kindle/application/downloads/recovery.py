"""Reconcilia o journal local de arquivos e metadados sem iniciar rede."""

from __future__ import annotations

from dataclasses import dataclass

from manga_to_kindle.application.downloads.errors import (
    DownloadImageInvalid,
    DownloadStorageError,
)
from manga_to_kindle.domain.download_job import DownloadState
from manga_to_kindle.domain.downloads import DownloadPage, DownloadPageState
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from manga_to_kindle.infrastructure.persistence.download_repository import (
    DownloadQueueSnapshot,
    DownloadRepository,
)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass(frozen=True, slots=True)
class RecoverySummary:
    interrupted_jobs: int
    completed_pages_recovered: int
    partial_files_removed: int


class DownloadRecovery:
    def __init__(self, repository: DownloadRepository, page_store: PageStore) -> None:
        self._repository = repository
        self._page_store = page_store

    def execute(self) -> RecoverySummary:
        snapshots = self._repository.recover_interrupted()
        completed = 0
        removed = 0
        for snapshot in snapshots:
            for page in snapshot.pages:
                if page.state is DownloadPageState.STAGING:
                    if self._recover_promoted_page(snapshot, page):
                        completed += 1
                    else:
                        if page.temporary_path is not None:
                            removed += self._remove_partial(snapshot, page)
                        self._repository.interrupt_page(snapshot.job.id, page.id)
                elif (
                    page.state is DownloadPageState.INTERRUPTED
                    and page.temporary_path is not None
                ):
                    removed += self._remove_partial(snapshot, page)
                    self._repository.interrupt_page(snapshot.job.id, page.id)
        return RecoverySummary(
            interrupted_jobs=sum(
                snapshot.job.state is DownloadState.INTERRUPTED for snapshot in snapshots
            ),
            completed_pages_recovered=completed,
            partial_files_removed=removed,
        )

    def _recover_promoted_page(self, snapshot: DownloadQueueSnapshot, page: DownloadPage) -> bool:
        if page.original_path is None or page.sha256 is None or page.byte_size is None:
            return False
        path = page.original_path
        content_type = _CONTENT_TYPES.get(path.suffix.lower())
        if content_type is None or not path.exists():
            return False
        try:
            image = self._page_store.validate_file(path, content_type)
        except (DownloadImageInvalid, DownloadStorageError):
            return False
        if image.sha256 != page.sha256 or image.byte_size != page.byte_size:
            return False
        self._repository.complete_page(snapshot.job.id, page.id)
        return True

    def _remove_partial(self, snapshot: DownloadQueueSnapshot, page: DownloadPage) -> int:
        path = page.temporary_path
        if path is None:
            return 0
        try:
            return int(
                self._page_store.remove_partial(
                    path,
                    job_id=snapshot.job.id,
                    page_id=page.id,
                )
            )
        except DownloadStorageError:
            return 0
