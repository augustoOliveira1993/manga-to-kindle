from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.settings.cache import (
    CacheCategory,
    CacheManifestItem,
    ClearRegenerableCache,
    PreviewCacheCleanup,
    RegisterCacheItem,
)
from manga_to_kindle.domain.settings import MIB
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.settings_repository import SettingsRepository


class MemoryManifest:
    def __init__(self, items: tuple[CacheManifestItem, ...] = ()) -> None:
        self.items = list(items)

    def list_cache_items(self, root_path: Path) -> tuple[CacheManifestItem, ...]:
        return tuple(item for item in self.items if item.root_path == root_path)

    def register_cache_item(self, item: CacheManifestItem) -> None:
        self.items = [
            existing
            for existing in self.items
            if (existing.root_path, existing.relative_path)
            != (item.root_path, item.relative_path)
        ]
        self.items.append(item)

    def delete_cache_item(self, item_id) -> None:
        self.items = [item for item in self.items if item.id != item_id]


def test_cleanup_deletes_only_manifested_cache_and_preserves_modified_files(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(tmp_path / "profile" / "data" / "state.sqlite3")
    database.initialize()
    repository = SettingsRepository(database)
    root = tmp_path / "cache"
    root.mkdir()
    original = root / "regenerable.bin"
    original.write_bytes(b"regenerable bytes")
    unknown = root / "untracked.bin"
    unknown.write_bytes(b"keep untracked")
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"keep outside")

    registered = RegisterCacheItem(repository).execute(
        original,
        root,
        category=CacheCategory.PREVIEW,
    )
    original.write_bytes(b"changed content!")
    preview = PreviewCacheCleanup(repository).execute(
        root,
        limit_bytes=100 * MIB,
        retention_days=30,
        clear_all=True,
    )
    result = ClearRegenerableCache(repository).execute(preview, confirmed=True)

    assert result.removed_count == 0
    assert result.preserved_count == 1
    assert original.read_bytes() == b"changed content!"
    assert unknown.read_bytes() == b"keep untracked"
    assert outside.read_bytes() == b"keep outside"
    assert repository.list_cache_items(root) == (registered,)
    database.close()


def test_cache_policy_removes_expired_and_least_recent_items_to_respect_quota(
    tmp_path: Path,
) -> None:
    root = tmp_path / "cache"
    now = datetime.now(UTC)
    items = (
        _manifest_item(root, "expired", 40 * timedelta(days=1), 40 * MIB),
        _manifest_item(root, "recent-small", timedelta(days=1), 40 * MIB),
        _manifest_item(root, "recent-large", timedelta(days=2), 70 * MIB),
    )
    preview = PreviewCacheCleanup(MemoryManifest(items)).execute(
        root,
        limit_bytes=100 * MIB,
        retention_days=30,
        now=now,
    )

    assert {item.relative_path.name for item in preview.files} == {
        "expired",
        "recent-large",
    }
    assert preview.total_bytes == 110 * MIB


def test_cache_cleanup_requires_explicit_confirmation(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    cache_file = root / "keep.bin"
    cache_file.write_bytes(b"keep until confirmation")
    database = SQLiteDatabase(tmp_path / "profile" / "data" / "state.sqlite3")
    database.initialize()
    repository = SettingsRepository(database)
    RegisterCacheItem(repository).execute(
        cache_file,
        root,
        category=CacheCategory.THUMBNAIL,
    )
    preview = PreviewCacheCleanup(repository).execute(
        root,
        limit_bytes=100 * MIB,
        retention_days=30,
        clear_all=True,
    )

    try:
        ClearRegenerableCache(repository).execute(preview, confirmed=False)
    except RuntimeError:
        pass
    else:
        raise AssertionError("A limpeza sem confirmação deveria falhar")

    assert cache_file.read_bytes() == b"keep until confirmation"
    database.close()


def test_cache_item_marked_in_use_after_preview_is_preserved(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    item = _manifest_item(root, "active-preview", timedelta(days=40), 1)
    store = MemoryManifest((item,))
    preview = PreviewCacheCleanup(store).execute(
        root,
        limit_bytes=100 * MIB,
        retention_days=30,
        clear_all=True,
    )
    store.items[0] = replace(item, in_use=True)

    result = ClearRegenerableCache(store).execute(preview, confirmed=True)

    assert result.removed_count == 0
    assert result.preserved_count == 1


def _manifest_item(
    root: Path,
    name: str,
    age: timedelta,
    size_bytes: int,
    *,
    in_use: bool = False,
) -> CacheManifestItem:
    return CacheManifestItem(
        id=uuid4(),
        root_path=root.resolve(),
        relative_path=Path(name),
        sha256="a" * 64,
        size_bytes=size_bytes,
        last_accessed_at=datetime.now(UTC) - age,
        in_use=in_use,
    )
