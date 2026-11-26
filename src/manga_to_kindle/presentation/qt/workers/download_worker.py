"""Adaptador da fila F005 ao OperationRunner e seus sinais Qt tipados."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from manga_to_kindle.application.downloads.queue import DownloadQueue, DownloadRunResult
from manga_to_kindle.domain.providers import MangaProvider, ProviderPageReference
from manga_to_kindle.presentation.qt.workers.adapter import (
    BackgroundOperation,
    CancellationToken,
    ProgressReporter,
)


def make_download_operation(
    queue: DownloadQueue,
    *,
    job_id: UUID,
    provider: MangaProvider,
    references: Mapping[tuple[UUID, str], ProviderPageReference],
) -> BackgroundOperation:
    """Executa persistência, rede e validação no worker sem tocar widgets."""

    def run(
        cancellation: CancellationToken,
        report: ProgressReporter,
    ) -> DownloadRunResult:
        return queue.execute(
            job_id=job_id,
            provider=provider,
            references=references,
            cancellation=cancellation,
            report_progress=report,
        )

    return run
