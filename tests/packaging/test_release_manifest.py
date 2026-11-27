from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from tools.release.manifest import ArtifactAttestation, ReleaseManifest


def _manifest() -> dict[str, object]:
    return {
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
        "bundle": {
            "format": "portable-archive",
            "pyinstaller_mode": "onedir",
            "installer_version": None,
        },
        "components": [
            {
                "name": "PyInstaller",
                "version": "6.22.3",
                "category": "python-package",
                "source_url": "https://pypi.org/project/pyinstaller/6.22.3/",
                "license_id": "GPL-2.0-only WITH PyInstaller-exception",
                "notice_path": "THIRD-PARTY-NOTICES.md",
                "included": True,
            }
        ],
        "artifacts": [
            {
                "name": "MangaToKindle-0.1.0-windows-x64-local.zip",
                "format": "portable-archive",
                "target_pair": {"windows": "Windows 10", "architecture": "x64"},
            }
        ],
    }


def test_release_manifest_validates_version_hashes_targets_and_components() -> None:
    manifest = ReleaseManifest.model_validate_json(json.dumps(_manifest()))

    assert manifest.product.version == "0.1.0"
    assert manifest.target_pairs[0].architecture == "x64"
    assert manifest.components[0].license_id.startswith("GPL-")


@pytest.mark.parametrize(
    "path,value",
    [
        (("product", "version"), "0.1"),
        (("source", "uv_lock_sha256"), "z" * 64),
        (("source", "commit_id"), "not-a-commit"),
        (("target_pairs",), []),
        (("components", 0, "license_id"), "UNKNOWN"),
    ],
)
def test_release_manifest_rejects_incomplete_or_unreviewed_inputs(
    path: tuple[str | int, ...], value: object
) -> None:
    manifest = _manifest()
    target: dict[str, object] | list[object] = manifest
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ValidationError):
        ReleaseManifest.model_validate_json(json.dumps(manifest))


def test_artifact_attestation_cannot_pass_with_pending_release_gates() -> None:
    attestation = {
        "schema_version": "1.0",
        "manifest_sha256": "a" * 64,
        "build_started_at_utc": "2026-11-26T12:00:00Z",
        "artifact_name": "MangaToKindle-local.zip",
        "artifact_format": "portable-archive",
        "target_pair": {"windows": "Windows 10", "architecture": "x64"},
        "artifact_sha256": "b" * 64,
        "gates": {
            "architecture_matrix": "pending",
            "license_review": "pending",
            "clean_vm_validation": "pending",
        },
        "result": "pending",
    }

    assert ArtifactAttestation.model_validate_json(json.dumps(attestation)).result == "pending"
    attestation["result"] = "passed"
    with pytest.raises(ValidationError):
        ArtifactAttestation.model_validate_json(json.dumps(attestation))
