"""Create a hash-bound attestation without overriding unresolved release gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from tools.release.manifest import (
    ArtifactAttestation,
    ReleaseGates,
    ReleaseManifest,
    TargetPair,
    resolve_release_file,
    sha256_file,
    validate_archive_notice_files,
    validate_distribution_archive,
)


def create_artifact_attestation(
    *,
    manifest_bytes: bytes,
    artifact_root: Path,
    artifact_name: str,
    target_pair: TargetPair,
    build_started_at_utc: datetime,
    gates: ReleaseGates,
) -> ArtifactAttestation:
    manifest = ReleaseManifest.model_validate_json(manifest_bytes)
    artifact_reference = next(
        (
            artifact
            for artifact in manifest.artifacts
            if artifact.name == artifact_name and artifact.target_pair == target_pair
        ),
        None,
    )
    if artifact_reference is None:
        raise ValueError("O artefato/par-alvo não está declarado no manifest de release.")

    artifact_path = resolve_release_file(
        artifact_root, artifact_name, item_label="artefato"
    )
    if artifact_reference.format == "portable-archive":
        validate_distribution_archive(artifact_path)
        if gates.license_review == "passed":
            if not manifest.components:
                raise ValueError("A revisão aprovada exige inventário de componentes.")
            validate_archive_notice_files(manifest, artifact_path)
    elif gates.license_review == "passed":
        raise ValueError("A validação de notices do instalador Inno ainda não está disponível.")

    gate_states = tuple(gates.model_dump().values())
    result: Literal["passed", "failed", "pending"] = (
        "failed" if "failed" in gate_states else "pending"
    )
    if all(state == "passed" for state in gate_states):
        result = "passed"

    return ArtifactAttestation(
        schema_version="1.0",
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        build_started_at_utc=build_started_at_utc,
        artifact_name=artifact_name,
        artifact_format=artifact_reference.format,
        target_pair=target_pair,
        artifact_sha256=sha256_file(str(artifact_path)),
        gates=gates,
        result=result,
    )


def write_attestation(attestation: ArtifactAttestation, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(attestation.model_dump(mode="json"), stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--target-windows", choices=("Windows 10", "Windows 11"), required=True)
    parser.add_argument("--target-architecture", choices=("x64", "ARM64", "x86"), required=True)
    parser.add_argument("--build-started-at-utc", required=True)
    parser.add_argument(
        "--architecture-matrix", choices=("pending", "passed", "failed"), default="pending"
    )
    parser.add_argument(
        "--license-review", choices=("pending", "passed", "failed"), default="pending"
    )
    parser.add_argument(
        "--clean-vm-validation", choices=("pending", "passed", "failed"), default="pending"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    build_started_at = datetime.fromisoformat(args.build_started_at_utc.replace("Z", "+00:00"))
    target_pair = TargetPair(
        windows=args.target_windows,
        architecture=args.target_architecture,
    )
    gates = ReleaseGates(
        architecture_matrix=args.architecture_matrix,
        license_review=args.license_review,
        clean_vm_validation=args.clean_vm_validation,
    )
    attestation = create_artifact_attestation(
        manifest_bytes=args.manifest.read_bytes(),
        artifact_root=args.artifact_root,
        artifact_name=args.artifact_name,
        target_pair=target_pair,
        build_started_at_utc=build_started_at,
        gates=gates,
    )
    write_attestation(attestation, args.output)
    print(f"Atestação {attestation.result}: {args.output}")
    print(f"SHA-256 do artefato: {attestation.artifact_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
