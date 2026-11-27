from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tools.release.bundle_inventory import build_bundle_inventory, write_bundle_inventory


def test_bundle_inventory_records_sorted_relative_paths_and_file_hashes(tmp_path: Path) -> None:
    bundle = tmp_path / "MangaToKindle"
    (bundle / "_internal" / "PySide6").mkdir(parents=True)
    (bundle / "MangaToKindle.exe").write_bytes(b"executable")
    qt_library = bundle / "_internal" / "PySide6" / "Qt6Core.dll"
    qt_library.write_bytes(b"qt library")

    inventory = build_bundle_inventory(bundle)

    assert inventory["file_count"] == 2
    assert inventory["total_size_bytes"] == len(b"executable") + len(b"qt library")
    assert inventory["license_review_status"] == "pending"
    assert [entry["path"] for entry in inventory["files"]] == [
        "MangaToKindle.exe",
        "_internal/PySide6/Qt6Core.dll",
    ]
    assert inventory["files"][1]["sha256"] == hashlib.sha256(b"qt library").hexdigest()
    serialized = json.dumps(inventory)
    assert str(tmp_path) not in serialized


def test_bundle_inventory_is_deterministic_and_written_atomically(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "app.exe").write_bytes(b"app")
    output = tmp_path / "output" / "inventory.json"

    expected = build_bundle_inventory(bundle)
    write_bundle_inventory(bundle, output)

    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert not list(output.parent.glob("*.tmp"))


def test_bundle_inventory_rejects_empty_directories(tmp_path: Path) -> None:
    bundle = tmp_path / "empty-bundle"
    bundle.mkdir()

    with pytest.raises(ValueError, match="não contém arquivos"):
        build_bundle_inventory(bundle)
