from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools.release.attestation import create_artifact_attestation, write_attestation
from tools.release.manifest import ReleaseGates, TargetPair


def _manifest_bytes() -> bytes:
    manifest = {
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
            "windows_build_image": "Windows 10 x64 build host",
        },
        "target_pairs": [{"windows": "Windows 10", "architecture": "x64"}],
        "bundle": {"format": "portable-archive", "pyinstaller_mode": "onedir"},
        "components": [],
        "artifacts": [
            {
                "name": "MangaToKindle.zip",
                "format": "portable-archive",
                "target_pair": {"windows": "Windows 10", "architecture": "x64"},
            }
        ],
    }
    return json.dumps(manifest).encode("utf-8")


def test_pending_attestation_uses_real_artifact_and_manifest_hashes(tmp_path: Path) -> None:
    artifact = tmp_path / "MangaToKindle.zip"
    artifact_bytes = b"bundle entry"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("MangaToKindle.exe", artifact_bytes)
    manifest_bytes = _manifest_bytes()
    gates = ReleaseGates(
        architecture_matrix="pending",
        license_review="pending",
        clean_vm_validation="pending",
    )

    attestation = create_artifact_attestation(
        manifest_bytes=manifest_bytes,
        artifact_root=tmp_path,
        artifact_name="MangaToKindle.zip",
        target_pair=TargetPair(windows="Windows 10", architecture="x64"),
        build_started_at_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
        gates=gates,
    )

    assert attestation.result == "pending"
    assert attestation.artifact_sha256 == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert attestation.manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()

    output = tmp_path / "evidence" / "attestation.json"
    write_attestation(attestation, output)
    assert json.loads(output.read_text(encoding="utf-8"))["result"] == "pending"
    assert not list(output.parent.glob("*.tmp"))


def test_passed_license_gate_requires_notice_inside_distribution(tmp_path: Path) -> None:
    artifact = tmp_path / "MangaToKindle.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("MangaToKindle.exe", b"bundle entry")
    gates = ReleaseGates(
        architecture_matrix="passed",
        license_review="passed",
        clean_vm_validation="passed",
    )

    manifest_bytes = _manifest_bytes().replace(
        b'"components": []',
        b'"components": [{"name":"runtime","version":"1","category":"runtime",'
        b'"source_url":"https://example.org/runtime","license_id":"MIT",'
        b'"notice_path":"THIRD-PARTY-NOTICES/runtime.txt","included":true}]',
    )

    with pytest.raises(ValueError, match="não está no ZIP distribuído"):
        create_artifact_attestation(
            manifest_bytes=manifest_bytes,
            artifact_root=tmp_path,
            artifact_name="MangaToKindle.zip",
            target_pair=TargetPair(windows="Windows 10", architecture="x64"),
            build_started_at_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
            gates=gates,
        )


def test_passed_attestation_hashes_notice_inside_distribution(tmp_path: Path) -> None:
    artifact = tmp_path / "MangaToKindle.zip"
    notice_path = "THIRD-PARTY-NOTICES/runtime.txt"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("MangaToKindle.exe", b"bundle entry")
        archive.writestr(notice_path, "Runtime license text\n")
    manifest_bytes = _manifest_bytes().replace(
        b'"components": []',
        b'"components": [{"name":"runtime","version":"1","category":"runtime",'
        b'"source_url":"https://example.org/runtime","license_id":"MIT",'
        b'"notice_path":"THIRD-PARTY-NOTICES/runtime.txt","included":true}]',
    )
    gates = ReleaseGates(
        architecture_matrix="passed",
        license_review="passed",
        clean_vm_validation="passed",
    )

    attestation = create_artifact_attestation(
        manifest_bytes=manifest_bytes,
        artifact_root=tmp_path,
        artifact_name="MangaToKindle.zip",
        target_pair=TargetPair(windows="Windows 10", architecture="x64"),
        build_started_at_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
        gates=gates,
    )

    assert attestation.result == "passed"


def test_attestation_rejects_artifacts_not_declared_in_manifest(tmp_path: Path) -> None:
    (tmp_path / "MangaToKindle.zip").write_bytes(b"test artifact")
    gates = ReleaseGates(
        architecture_matrix="pending",
        license_review="pending",
        clean_vm_validation="pending",
    )

    with pytest.raises(ValueError, match="não está declarado"):
        create_artifact_attestation(
            manifest_bytes=_manifest_bytes(),
            artifact_root=tmp_path,
            artifact_name="other.zip",
            target_pair=TargetPair(windows="Windows 10", architecture="x64"),
            build_started_at_utc=datetime(2026, 11, 26, 12, 0, tzinfo=UTC),
            gates=gates,
        )
