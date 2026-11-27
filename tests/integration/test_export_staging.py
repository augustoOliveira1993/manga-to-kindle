from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.infrastructure.exports.output_store import (
    ExportOutputConflict,
    ExportOutputError,
    ExportOutputStore,
)


def test_output_is_promoted_into_selected_folder_without_overwrite(tmp_path: Path) -> None:
    store = ExportOutputStore(tmp_path)
    staged = store.begin(uuid4(), "Coleção - Volume 1.cbz")
    staged.staged_path.write_bytes(b"first package")

    final_path = store.publish(staged)

    assert final_path == tmp_path / "Coleção - Volume 1.cbz"
    assert final_path.read_bytes() == b"first package"
    assert not staged.staging_directory.exists()


def test_mobi_output_is_supported_by_atomic_local_staging(tmp_path: Path) -> None:
    store = ExportOutputStore(tmp_path)
    staged = store.begin(uuid4(), "Coleção — Volume 1.mobi")
    staged.staged_path.write_bytes(b"verified MOBI output")

    final_path = store.publish(staged)

    assert final_path == tmp_path / "Coleção — Volume 1.mobi"
    assert final_path.read_bytes() == b"verified MOBI output"


def test_existing_output_needs_confirmation_and_is_preserved_on_cancel(tmp_path: Path) -> None:
    destination = tmp_path / "book.epub"
    destination.write_bytes(b"existing")
    store = ExportOutputStore(tmp_path)

    with pytest.raises(ExportOutputConflict):
        store.begin(uuid4(), destination.name)

    staged = store.begin(uuid4(), destination.name, overwrite_confirmed=True)
    staged.staged_path.write_bytes(b"replacement")
    store.cleanup(staged)

    assert destination.read_bytes() == b"existing"


def test_confirmed_overwrite_replaces_only_the_file_confirmed_at_start(tmp_path: Path) -> None:
    destination = tmp_path / "book.cbz"
    destination.write_bytes(b"existing")
    store = ExportOutputStore(tmp_path)
    staged = store.begin(uuid4(), destination.name, overwrite_confirmed=True)
    staged.staged_path.write_bytes(b"replacement")
    destination.write_bytes(b"changed after confirmation")

    with pytest.raises(ExportOutputConflict, match="mudou"):
        store.publish(staged)

    assert destination.read_bytes() == b"changed after confirmation"


@pytest.mark.parametrize("filename", ("../escape.cbz", "sub/book.epub", "bad.txt", ".."))
def test_unsafe_or_unexpected_output_names_are_rejected(tmp_path: Path, filename: str) -> None:
    store = ExportOutputStore(tmp_path)

    with pytest.raises(ExportOutputError):
        store.begin(uuid4(), filename)


def test_publish_rejects_missing_staged_file_and_cleanup_is_idempotent(tmp_path: Path) -> None:
    store = ExportOutputStore(tmp_path)
    staged = store.begin(uuid4(), "book.cbz")

    with pytest.raises(ExportOutputError):
        store.publish(staged)

    store.cleanup(staged)
    store.cleanup(staged)
    assert not (tmp_path / "book.cbz").exists()
