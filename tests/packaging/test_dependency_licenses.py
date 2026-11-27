from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from tools.release.manifest import PackagedComponent, ReleaseManifest, validate_notice_files


def _component() -> dict[str, object]:
    return {
        "name": "sample-package",
        "version": "1.0.0",
        "category": "python-package",
        "source_url": "https://pypi.org/project/sample-package/1.0.0/",
        "license_id": "MIT",
        "notice_path": "THIRD-PARTY-NOTICES/sample-package.txt",
        "included": True,
    }


def test_component_requires_explicit_notice_path_field() -> None:
    component = _component()
    del component["notice_path"]

    with pytest.raises(ValidationError, match="notice_path"):
        PackagedComponent.model_validate(component)


def test_unknown_component_license_blocks_release_manifest() -> None:
    component = _component()
    component["license_id"] = "UNKNOWN"

    with pytest.raises(ValidationError, match="licença não revisada"):
        PackagedComponent.model_validate(component)


def test_notice_path_may_be_null_only_when_explicitly_declared() -> None:
    component = _component()
    component["notice_path"] = None

    parsed = PackagedComponent.model_validate(component)

    assert parsed.notice_path is None


def test_notice_inventory_verifies_distributed_text_and_hash(tmp_path: Path) -> None:
    manifest_data = {
        "schema_version": "1.0",
        "product": {"name": "Manga to Kindle", "version": "0.1.0"},
        "source": {
            "commit_id": "a" * 40,
            "uv_lock_sha256": "b" * 64,
            "pyinstaller_spec_sha256": "c" * 64,
        },
        "toolchain": {
            "python": "3.12.16",
            "uv": "0.13.9",
            "pyinstaller": "6.22.3",
            "windows_build_image": "Windows 10 x64 local build",
        },
        "target_pairs": [{"windows": "Windows 10", "architecture": "x64"}],
        "bundle": {"format": "portable-archive", "pyinstaller_mode": "onedir"},
        "components": [
            {
                **_component(),
                "notice_path": "THIRD-PARTY-NOTICES/sample-package.txt",
            }
        ],
        "artifacts": [
            {
                "name": "package.zip",
                "format": "portable-archive",
                "target_pair": {"windows": "Windows 10", "architecture": "x64"},
            }
        ],
    }
    manifest = ReleaseManifest.model_validate_json(json.dumps(manifest_data))
    notice = tmp_path / "THIRD-PARTY-NOTICES" / "sample-package.txt"
    notice.parent.mkdir()
    content = b"Sample package license notice\n"
    notice.write_bytes(content)

    entries = validate_notice_files(manifest, tmp_path)

    assert entries == [
        {
            "component": "sample-package",
            "path": "THIRD-PARTY-NOTICES/sample-package.txt",
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "status": "present",
        }
    ]


def test_notice_inventory_rejects_missing_or_empty_declared_files(tmp_path: Path) -> None:
    manifest_data = {
        "schema_version": "1.0",
        "product": {"name": "Manga to Kindle", "version": "0.1.0"},
        "source": {
            "commit_id": "a" * 40,
            "uv_lock_sha256": "b" * 64,
            "pyinstaller_spec_sha256": "c" * 64,
        },
        "toolchain": {
            "python": "3.12.16",
            "uv": "0.13.9",
            "pyinstaller": "6.22.3",
            "windows_build_image": "Windows 10 x64 local build",
        },
        "target_pairs": [{"windows": "Windows 10", "architecture": "x64"}],
        "bundle": {"format": "portable-archive", "pyinstaller_mode": "onedir"},
        "components": [{**_component(), "notice_path": "THIRD-PARTY-NOTICES/sample.txt"}],
        "artifacts": [
            {
                "name": "package.zip",
                "format": "portable-archive",
                "target_pair": {"windows": "Windows 10", "architecture": "x64"},
            }
        ],
    }
    manifest = ReleaseManifest.model_validate_json(json.dumps(manifest_data))

    with pytest.raises(ValueError, match="não existe"):
        validate_notice_files(manifest, tmp_path)

    notice = tmp_path / "THIRD-PARTY-NOTICES" / "sample.txt"
    notice.parent.mkdir()
    notice.write_bytes(b" \n")
    with pytest.raises(ValueError, match="está vazio"):
        validate_notice_files(manifest, tmp_path)
