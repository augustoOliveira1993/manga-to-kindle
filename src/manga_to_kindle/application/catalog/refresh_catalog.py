"""Substituição transacional do snapshot após consulta completa e validação."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from manga_to_kindle.application.catalog.errors import CatalogRefreshCancelled
from manga_to_kindle.domain.catalog import CatalogSnapshot


class CatalogQuery(Protocol):
    def execute(
        self,
        value: str,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> CatalogSnapshot: ...


class CatalogWriter(Protocol):
    def replace(self, snapshot: CatalogSnapshot) -> None: ...


class RefreshCatalog:
    def __init__(self, query: CatalogQuery, repository: CatalogWriter) -> None:
        self._query = query
        self._repository = repository

    def execute(
        self,
        value: str,
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> CatalogSnapshot:
        cancelled = is_cancelled or (lambda: False)
        if cancelled():
            raise CatalogRefreshCancelled("A consulta foi cancelada.")
        snapshot = self._query.execute(value, is_cancelled=cancelled)
        if cancelled():
            raise CatalogRefreshCancelled("A atualização foi cancelada antes de ser salva.")
        self._repository.replace(snapshot)
        return snapshot
