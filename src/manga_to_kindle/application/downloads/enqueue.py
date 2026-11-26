"""Valida autorização e destinos antes de persistir qualquer trabalho."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from manga_to_kindle.application.downloads.errors import (
    DownloadSelectionInvalid,
    DownloadUnavailable,
)
from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.providers import (
    MangaProvider,
    ProviderError,
    ProviderPageReference,
)
from manga_to_kindle.infrastructure.network.url_policy import ExternalUrlPolicy
from manga_to_kindle.infrastructure.persistence.download_repository import (
    ChapterPageReferences,
    DownloadQueueSnapshot,
    DownloadRepository,
)


class EnqueueDownload:
    def __init__(
        self,
        repository: DownloadRepository,
        url_policy: ExternalUrlPolicy,
    ) -> None:
        self._repository = repository
        self._url_policy = url_policy

    def execute(
        self,
        *,
        provider: MangaProvider,
        catalog: CatalogSnapshot,
        selected_chapter_ids: Iterable[UUID],
    ) -> DownloadQueueSnapshot:
        capabilities = provider.capabilities
        if (
            provider.provider_id != catalog.provider_id
            or catalog.simulated
            or capabilities.simulated
            or capabilities.requires_authentication
            or not capabilities.page_references
            or not capabilities.download_enabled
        ):
            raise DownloadUnavailable(
                "Este provedor não tem autorização verificável para baixar conteúdo localmente."
            )

        selected = tuple(selected_chapter_ids)
        if not selected or len(set(selected)) != len(selected):
            raise DownloadSelectionInvalid("Selecione capítulos válidos sem repetições.")
        by_id = {chapter.id: chapter for chapter in catalog.chapters}
        if any(chapter_id not in by_id for chapter_id in selected):
            raise DownloadSelectionInvalid("A seleção contém capítulo fora do catálogo atual.")
        ordered_chapters = tuple(
            sorted(
                (by_id[chapter_id] for chapter_id in selected),
                key=lambda chapter: chapter.position,
            )
        )

        chapter_pages: list[ChapterPageReferences] = []
        for chapter in ordered_chapters:
            try:
                references = tuple(provider.get_pages(chapter))
            except Exception as exc:
                code = getattr(getattr(exc, "code", None), "value", getattr(exc, "code", None))
                safe_code = code if isinstance(code, str) and code.isupper() else "PROVIDER_FAILED"
                raise DownloadUnavailable(
                    f"O provedor não conseguiu preparar as páginas ({safe_code})."
                ) from None
            self._validate_references(provider, references)
            chapter_pages.append((chapter, references))

        policy_snapshot: dict[str, object] = {
            "provider_id": provider.provider_id,
            "authorization_reviewed_on": capabilities.authorization_reviewed_on.isoformat()
            if capabilities.authorization_reviewed_on is not None
            else None,
            "allowed_hosts": sorted(capabilities.allowed_hosts),
            "allowed_ports": sorted(capabilities.allowed_ports),
            "allowed_schemes": sorted(capabilities.allowed_schemes),
            "requests_per_minute": capabilities.requests_per_minute,
        }
        return self._repository.enqueue(
            manga_id=catalog.manga.id,
            provider_id=provider.provider_id,
            chapter_pages=chapter_pages,
            policy_snapshot=policy_snapshot,
        )

    def _validate_references(
        self,
        provider: MangaProvider,
        references: tuple[ProviderPageReference, ...],
    ) -> None:
        if not references:
            raise DownloadSelectionInvalid("O capítulo selecionado não possui páginas disponíveis.")
        if any(reference.simulated for reference in references):
            raise DownloadUnavailable("Referências de demonstração não podem ser baixadas.")
        if len({reference.source_id for reference in references}) != len(references):
            raise DownloadSelectionInvalid("O provedor retornou IDs de página repetidos.")
        if len({reference.position for reference in references}) != len(references):
            raise DownloadSelectionInvalid("O provedor retornou posições repetidas.")
        capabilities = provider.capabilities
        for reference in references:
            try:
                self._url_policy.validate(
                    reference.destination,
                    allowed_hosts=capabilities.allowed_hosts,
                    allowed_ports=capabilities.allowed_ports,
                    allowed_schemes=capabilities.allowed_schemes,
                )
            except ProviderError:
                raise DownloadUnavailable(
                    "Um destino de página não está autorizado para este provedor."
                ) from None
