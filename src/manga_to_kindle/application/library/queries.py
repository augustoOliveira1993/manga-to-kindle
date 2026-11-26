"""Casos de uso de consulta e favoritos da biblioteca."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from manga_to_kindle.domain.library import (
    LibraryActivity,
    LibraryAsset,
    LibraryDeletionPreview,
    LibraryDeletionResult,
    LibraryPage,
    LibraryPreferences,
    LibraryQuery,
)


class LibraryRepositoryPort(Protocol):
    def search(self, query: LibraryQuery) -> LibraryPage: ...

    def history(self, *, limit: int = 100) -> tuple[LibraryActivity, ...]: ...

    def set_favorite(self, *, manga_id: UUID, chapter_id: UUID | None, favorite: bool) -> None: ...

    def get_preferences(self) -> LibraryPreferences: ...

    def save_preferences(self, preferences: LibraryPreferences) -> None: ...

    def preview_delete(self, manga_id: UUID) -> LibraryDeletionPreview: ...

    def delete_scope(
        self,
        preview: LibraryDeletionPreview,
        *,
        asset_ids: tuple[str, ...],
        confirmed: bool,
    ) -> LibraryDeletionResult: ...

    def list_unlinked_assets(self) -> tuple[LibraryAsset, ...]: ...

    def delete_unlinked_assets(
        self,
        asset_ids: tuple[str, ...],
        *,
        confirmed: bool,
    ) -> LibraryDeletionResult: ...

    def recover_deletions(self) -> int: ...


class QueryLibrary:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, query: LibraryQuery) -> LibraryPage:
        return self._repository.search(query)


class QueryLibraryHistory:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, *, limit: int = 100) -> tuple[LibraryActivity, ...]:
        return self._repository.history(limit=limit)


class SetLibraryFavorite:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, *, manga_id: UUID, chapter_id: UUID | None, favorite: bool) -> None:
        self._repository.set_favorite(
            manga_id=manga_id,
            chapter_id=chapter_id,
            favorite=favorite,
        )


class LoadLibraryPreferences:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self) -> LibraryPreferences:
        return self._repository.get_preferences()


class SaveLibraryPreferences:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, preferences: LibraryPreferences) -> None:
        self._repository.save_preferences(preferences)


class PreviewLibraryDelete:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self, manga_id: UUID) -> LibraryDeletionPreview:
        return self._repository.preview_delete(manga_id)


class DeleteLibraryScope:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        preview: LibraryDeletionPreview,
        *,
        asset_ids: tuple[str, ...],
        confirmed: bool,
    ) -> LibraryDeletionResult:
        return self._repository.delete_scope(
            preview,
            asset_ids=asset_ids,
            confirmed=confirmed,
        )


class ListUnlinkedLibraryAssets:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(self) -> tuple[LibraryAsset, ...]:
        return self._repository.list_unlinked_assets()


class DeleteUnlinkedLibraryAssets:
    def __init__(self, repository: LibraryRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        asset_ids: tuple[str, ...],
        *,
        confirmed: bool,
    ) -> LibraryDeletionResult:
        return self._repository.delete_unlinked_assets(asset_ids, confirmed=confirmed)
