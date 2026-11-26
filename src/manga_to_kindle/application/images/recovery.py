"""Reconcilia importações interrompidas durante o encerramento do aplicativo."""

from __future__ import annotations

from manga_to_kindle.application.images.ports import ImageImportRepositoryPort, ImageStorePort


class RecoverImageImports:
    def __init__(self, repository: ImageImportRepositoryPort, store: ImageStorePort) -> None:
        self._repository = repository
        self._store = store

    def execute(self) -> int:
        recovered = 0
        for job_id in self._repository.staging_jobs():
            self._store.cleanup(job_id, include_final=True)
            self._repository.mark_interrupted(job_id)
            recovered += 1
        return recovered
