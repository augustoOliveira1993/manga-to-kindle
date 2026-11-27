"""Rebuilds authorized page destinations from persisted source identities on explicit resume."""

from __future__ import annotations

from types import MappingProxyType
from uuid import UUID

from manga_to_kindle.application.downloads.enqueue import PreparedDownload
from manga_to_kindle.application.downloads.errors import DownloadRecordNotFound, DownloadUnavailable
from manga_to_kindle.application.providers.registry import ProviderRegistry
from manga_to_kindle.domain.downloads import DownloadPageState
from manga_to_kindle.domain.providers import ProviderPageReference
from manga_to_kindle.infrastructure.persistence.download_repository import DownloadRepository


class RestoreDownloadReferences:
    """Restores references only when a provider can derive them from the persisted item ID."""

    def __init__(self, repository: DownloadRepository, providers: ProviderRegistry) -> None:
        self._repository = repository
        self._providers = providers

    def execute(self, job_id: UUID) -> PreparedDownload:
        snapshot = self._repository.get(job_id)
        if snapshot is None:
            raise DownloadRecordNotFound("O trabalho não foi encontrado.")
        policy = self._repository.get_policy_snapshot(job_id)
        if policy is None:
            raise DownloadUnavailable("A autorização registrada não está disponível.")
        source_id = policy.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise DownloadUnavailable("A identidade de origem não está registrada.")
        try:
            provider = self._providers.by_id(snapshot.job.provider_id or "")
        except Exception:
            raise DownloadUnavailable("O provedor do trabalho não está disponível.") from None
        restorer = getattr(provider, "restore_page_reference", None)
        if not callable(restorer):
            raise DownloadUnavailable("Este provedor não oferece retomada segura após reinício.")

        references: dict[tuple[UUID, str], ProviderPageReference] = {}
        try:
            for page in snapshot.pages:
                if page.state is DownloadPageState.COMPLETE:
                    continue
                reference = restorer(source_id, page.source_page_id, page.position)
                if not isinstance(reference, ProviderPageReference):
                    raise DownloadUnavailable("A identidade de página não pôde ser restaurada.")
                references[(page.chapter_id, page.source_page_id)] = reference
        except DownloadUnavailable:
            raise
        except Exception:
            raise DownloadUnavailable("A identidade de página não pôde ser restaurada.") from None
        if not references:
            raise DownloadUnavailable("Não há páginas pendentes para retomar.")
        return PreparedDownload(
            snapshot=snapshot,
            provider=provider,
            page_references=MappingProxyType(references),
        )
