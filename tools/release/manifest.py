"""Typed validation for the release manifest and artifact attestation contracts."""

from __future__ import annotations

import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Sha256 = str
ProductVersion = str


class ReleaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Product(ReleaseModel):
    name: str = Field(min_length=1)
    version: ProductVersion = Field(
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
    )
    description: str | None = None
    publisher: str | None = None
    copyright: str | None = None


class Source(ReleaseModel):
    commit_id: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    uv_lock_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    pyinstaller_spec_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")


class Toolchain(ReleaseModel):
    python: str = Field(min_length=1)
    uv: str = Field(min_length=1)
    pyinstaller: str = Field(min_length=1)
    windows_build_image: str = Field(min_length=1)


class TargetPair(ReleaseModel):
    windows: Literal["Windows 10", "Windows 11"]
    architecture: Literal["x64", "ARM64", "x86"]


class Bundle(ReleaseModel):
    format: Literal["portable-archive", "inno-installer"]
    pyinstaller_mode: Literal["onedir"]
    installer_version: str | None = None


class PackagedComponent(ReleaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    category: Literal["runtime", "python-package", "qt-plugin", "resource", "native-library"]
    source_url: HttpUrl
    license_id: str = Field(min_length=1)
    copyright: str | None = None
    notice_path: str | None
    included: Literal[True]

    @model_validator(mode="after")
    def require_reviewed_license(self) -> PackagedComponent:
        if self.license_id.upper() in {"UNKNOWN", "NOASSERTION", "NONE"}:
            raise ValueError("Componentes com licença não revisada bloqueiam a release.")
        if self.notice_path is not None:
            _validate_relative_path(self.notice_path)
        return self


class ArtifactReference(ReleaseModel):
    name: str = Field(min_length=1)
    format: Literal["portable-archive", "inno-installer"]
    target_pair: TargetPair

    @model_validator(mode="after")
    def require_relative_name(self) -> ArtifactReference:
        _validate_relative_path(self.name)
        return self


class ReleaseManifest(ReleaseModel):
    schema_version: Literal["1.0"]
    product: Product
    source: Source
    toolchain: Toolchain
    target_pairs: tuple[TargetPair, ...] = Field(min_length=1)
    bundle: Bundle
    components: tuple[PackagedComponent, ...]
    artifacts: tuple[ArtifactReference, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def artifacts_match_targets(self) -> ReleaseManifest:
        supported = set(self.target_pairs)
        if any(artifact.target_pair not in supported for artifact in self.artifacts):
            raise ValueError("Todo artefato deve corresponder a um par-alvo declarado.")
        return self


class ReleaseGates(ReleaseModel):
    architecture_matrix: Literal["pending", "passed", "failed"]
    license_review: Literal["pending", "passed", "failed"]
    clean_vm_validation: Literal["pending", "passed", "failed"]


class ArtifactAttestation(ReleaseModel):
    schema_version: Literal["1.0"]
    manifest_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    build_started_at_utc: AwareDatetime
    artifact_name: str = Field(min_length=1)
    artifact_format: Literal["portable-archive", "inno-installer"]
    target_pair: TargetPair
    artifact_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    gates: ReleaseGates
    result: Literal["passed", "failed", "pending"]

    @model_validator(mode="after")
    def passed_requires_all_gates(self) -> ArtifactAttestation:
        _validate_relative_path(self.artifact_name)
        if self.result == "passed" and any(
            state != "passed" for state in self.gates.model_dump().values()
        ):
            raise ValueError(
                "Uma atestação não passa enquanto algum gate de release estiver pendente."
            )
        return self


def validate_notice_files(
    manifest: ReleaseManifest, package_root: Path
) -> list[dict[str, str | int]]:
    """Verify declared third-party notice files exist in the package tree.

    This checks packaging presence and hashes only. It does not determine whether a
    license requires a notice or whether its legal text is complete.
    """
    if _is_reparse_point(package_root):
        raise ValueError("A raiz de notices não pode ser link ou ponto de nova análise.")
    root = package_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("A raiz de notices precisa ser um diretório.")

    notices: list[dict[str, str | int]] = []
    for component in manifest.components:
        if component.notice_path is None:
            notices.append({"component": component.name, "status": "not-required-declared"})
            continue

        notice_path = resolve_release_file(root, component.notice_path, item_label="notice")
        content = notice_path.read_bytes()
        if not content.strip():
            raise ValueError(
                f"O arquivo de notice declarado para {component.name} está vazio."
            )
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(
                f"O arquivo de notice de {component.name} não é texto UTF-8 válido."
            ) from error
        notices.append(
            {
                "component": component.name,
                "path": component.notice_path,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "status": "present",
            }
        )
    return notices


def validate_distribution_archive(archive_path: Path) -> None:
    """Reject corrupt or unsafe portable ZIP entries before release attestation."""
    if _is_reparse_point(archive_path):
        raise ValueError("O pacote não pode ser link ou ponto de nova análise.")
    if not archive_path.is_file():
        raise ValueError("O pacote precisa ser um arquivo ZIP regular.")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            seen: set[str] = set()
            for info in archive.infolist():
                normalized = info.filename.replace("\\", "/")
                _validate_relative_path(normalized.rstrip("/"))
                casefolded = normalized.casefold()
                if casefolded in seen:
                    raise ValueError("O pacote contém caminhos duplicados no ZIP.")
                seen.add(casefolded)
                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise ValueError("O pacote não pode conter links simbólicos.")
            damaged_entry = archive.testzip()
            if damaged_entry is not None:
                raise ValueError("O pacote ZIP contém dados corrompidos.")
    except zipfile.BadZipFile as error:
        raise ValueError("O pacote não é um ZIP válido.") from error


def validate_archive_notice_files(
    manifest: ReleaseManifest, archive_path: Path
) -> list[dict[str, str | int]]:
    """Verify declared notices are present and readable inside the distributed ZIP."""
    validate_distribution_archive(archive_path)
    notices: list[dict[str, str | int]] = []
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = {
                info.filename.replace("\\", "/").casefold(): info
                for info in archive.infolist()
            }
            for component in manifest.components:
                if component.notice_path is None:
                    notices.append(
                        {"component": component.name, "status": "not-required-declared"}
                    )
                    continue
                normalized_path = component.notice_path.replace("\\", "/")
                info = members.get(normalized_path.casefold())
                if info is None or info.is_dir():
                    raise ValueError(
                        f"O notice de {component.name} não está no ZIP distribuído."
                    )
                content = archive.read(info)
                if not content.strip():
                    raise ValueError(f"O notice de {component.name} está vazio no ZIP.")
                try:
                    content.decode("utf-8-sig")
                except UnicodeDecodeError as error:
                    raise ValueError(
                        f"O notice de {component.name} não é texto UTF-8 válido."
                    ) from error
                notices.append(
                    {
                        "component": component.name,
                        "path": normalized_path,
                        "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "status": "present",
                    }
                )
    except zipfile.BadZipFile as error:
        raise ValueError("O pacote não é um ZIP válido.") from error
    return notices


def sha256_file(path: str) -> Sha256:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_relative_path(value: str) -> None:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not value
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        raise ValueError("O caminho da release precisa ser relativo e ficar dentro do pacote.")


def resolve_release_file(package_root: Path, relative_path: str, *, item_label: str) -> Path:
    if _is_reparse_point(package_root):
        raise ValueError("A raiz do pacote não pode ser link ou ponto de nova análise.")
    root = package_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("A raiz do pacote precisa ser um diretório.")

    normalized = relative_path.replace("\\", "/")
    _validate_relative_path(normalized)
    current = root
    for part in PurePosixPath(normalized).parts:
        current = current / part
        try:
            is_reparse = _is_reparse_point(current)
        except FileNotFoundError as error:
            raise ValueError(f"O arquivo de {item_label} não existe: {relative_path}") from error
        if is_reparse:
            raise ValueError("O pacote não pode resolver arquivos por links ou junctions.")

    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"O arquivo de {item_label} precisa estar dentro do diretório do pacote.")
    return resolved


def _is_reparse_point(path: Path) -> bool:
    metadata = path.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_attribute
    )
