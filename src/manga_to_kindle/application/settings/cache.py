"""Manifest-based cleanup for files explicitly marked as regenerable cache."""

from __future__ import annotations

import hashlib
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from manga_to_kindle.domain.settings import GIB, MIB


class CacheCategory(StrEnum):
    PREVIEW = "preview"
    THUMBNAIL = "thumbnail"


@dataclass(frozen=True, slots=True)
class CacheManifestItem:
    id: UUID
    root_path: Path
    relative_path: Path
    sha256: str
    size_bytes: int
    last_accessed_at: datetime
    category: CacheCategory = CacheCategory.PREVIEW
    in_use: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.id, UUID)
            or not self.root_path.is_absolute()
            or self.relative_path.is_absolute()
            or ".." in self.relative_path.parts
            or not re.fullmatch(r"[0-9a-f]{64}", self.sha256)
            or type(self.size_bytes) is not int
            or self.size_bytes < 0
            or self.last_accessed_at.tzinfo is None
            or not isinstance(self.category, CacheCategory)
            or type(self.in_use) is not bool
        ):
            raise CacheCleanupError("O registro de cache contém dados inválidos.")


@dataclass(frozen=True, slots=True)
class CacheCleanupPreview:
    file_count: int
    total_bytes: int
    files: tuple[CacheManifestItem, ...]


@dataclass(frozen=True, slots=True)
class CacheCleanupResult:
    removed_count: int
    removed_bytes: int
    preserved_count: int


class CacheManifestStore(Protocol):
    def list_cache_items(self, root_path: Path) -> tuple[CacheManifestItem, ...]: ...

    def delete_cache_item(self, item_id: UUID) -> None: ...

    def register_cache_item(self, item: CacheManifestItem) -> None: ...


class CacheCleanupError(RuntimeError):
    code = "CACHE_CLEANUP_FAILED"


class CacheItemChanged(CacheCleanupError):
    code = "CACHE_ITEM_CHANGED"


class RegisterCacheItem:
    def __init__(self, store: CacheManifestStore) -> None:
        self._store = store

    def execute(
        self,
        path: Path,
        root_path: Path,
        *,
        category: CacheCategory,
        in_use: bool = False,
    ) -> CacheManifestItem:
        root = root_path.resolve(strict=True)
        if root_path.is_symlink() or not root.is_dir() or path.is_symlink():
            raise CacheCleanupError("O diretório de cache ou o arquivo não é seguro.")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("not regular")
            digest = _sha256(path)
        except (OSError, ValueError):
            raise CacheCleanupError("O item não pertence ao cache regenerável.") from None
        item = CacheManifestItem(
            id=uuid4(),
            root_path=root,
            relative_path=resolved.relative_to(root),
            sha256=digest,
            size_bytes=metadata.st_size,
            last_accessed_at=datetime.fromtimestamp(metadata.st_atime, UTC),
            category=category,
            in_use=in_use,
        )
        self._store.register_cache_item(item)
        registered = next(
            (
                candidate
                for candidate in self._store.list_cache_items(root)
                if candidate.relative_path == item.relative_path
            ),
            None,
        )
        if registered is None:
            raise CacheCleanupError("O manifesto não confirmou o item de cache.")
        return registered


class PreviewCacheCleanup:
    def __init__(self, store: CacheManifestStore) -> None:
        self._store = store

    def execute(
        self,
        root_path: Path,
        *,
        limit_bytes: int,
        retention_days: int,
        clear_all: bool = False,
        now: datetime | None = None,
    ) -> CacheCleanupPreview:
        current_time = now or datetime.now(UTC)
        if (
            current_time.tzinfo is None
            or type(limit_bytes) is not int
            or not 100 * MIB <= limit_bytes <= 20 * GIB
            or type(retention_days) is not int
            or not 1 <= retention_days <= 365
        ):
            raise CacheCleanupError("A política de retenção não é válida.")
        items = tuple(
            sorted(
                (
                    item
                    for item in self._store.list_cache_items(root_path.resolve(strict=False))
                    if item.category in {CacheCategory.PREVIEW, CacheCategory.THUMBNAIL}
                    and not item.in_use
                ),
                key=lambda item: (item.last_accessed_at, item.relative_path.as_posix()),
            )
        )
        if clear_all:
            selected = items
        else:
            expiration = current_time - timedelta(days=retention_days)
            expired = [item for item in items if item.last_accessed_at < expiration]
            selected_ids = {item.id for item in expired}
            remaining_size = sum(item.size_bytes for item in items if item.id not in selected_ids)
            for item in items:
                if remaining_size <= limit_bytes:
                    break
                if item.id in selected_ids:
                    continue
                selected_ids.add(item.id)
                remaining_size -= item.size_bytes
            selected = tuple(item for item in items if item.id in selected_ids)
        return CacheCleanupPreview(
            file_count=len(selected),
            total_bytes=sum(item.size_bytes for item in selected),
            files=selected,
        )


class ClearRegenerableCache:
    def __init__(self, store: CacheManifestStore) -> None:
        self._store = store

    def execute(self, preview: CacheCleanupPreview, *, confirmed: bool) -> CacheCleanupResult:
        if not confirmed:
            raise CacheCleanupError("A limpeza do cache não foi confirmada.")
        removed_count = 0
        removed_bytes = 0
        preserved_count = 0
        for item in preview.files:
            current = next(
                (
                    candidate
                    for candidate in self._store.list_cache_items(item.root_path)
                    if candidate.id == item.id
                ),
                None,
            )
            if current != item or current is None or current.in_use:
                preserved_count += 1
                continue
            try:
                self._remove_item(item)
            except CacheItemChanged:
                preserved_count += 1
                continue
            removed_count += 1
            removed_bytes += item.size_bytes
            self._store.delete_cache_item(item.id)
        return CacheCleanupResult(removed_count, removed_bytes, preserved_count)

    @staticmethod
    def _remove_item(item: CacheManifestItem) -> None:
        if (
            item.root_path.is_symlink()
            or item.relative_path.is_absolute()
            or ".." in item.relative_path.parts
        ):
            raise CacheItemChanged("O manifesto de cache não aponta para um caminho seguro.")
        root = item.root_path.resolve(strict=True)
        if not root.is_dir():
            raise CacheItemChanged("A pasta de cache não está disponível.")
        candidate = root / item.relative_path
        if candidate.is_symlink():
            raise CacheItemChanged("Um item do manifesto mudou e foi preservado.")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
            metadata = candidate.stat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size != item.size_bytes
                or _sha256(candidate) != item.sha256
            ):
                raise CacheItemChanged("Um item do manifesto mudou e foi preservado.")
            candidate.unlink()
        except CacheItemChanged:
            raise
        except (OSError, ValueError):
            raise CacheItemChanged(
                "Um item do manifesto não pôde ser validado e foi preservado."
            ) from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
