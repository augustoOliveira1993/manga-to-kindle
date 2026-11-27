"""Map PyInstaller bundle files to source distributions and runtime candidates."""

from __future__ import annotations

import argparse
import ast
import json
import os
import stat
import sys
import sysconfig
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib.metadata import Distribution, distributions
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import quote

ROOT = Path(__file__).parents[2]
DEFAULT_TOC = ROOT / "build" / "MangaToKindle" / "COLLECT-00.toc"
DEFAULT_OUTPUT = (
    ROOT / "packaging" / "third-party-notices" / "bundle-component-candidates.json"
)


@dataclass(frozen=True, slots=True)
class DistributionCandidate:
    name: str
    version: str
    project_url: str
    license_metadata: dict[str, object] | None
    license_file_paths: tuple[str, ...]
    files: tuple[Path, ...]


def build_component_inventory(
    toc_path: Path,
    *,
    site_packages: Path | None = None,
    python_root: Path | None = None,
    windows_root: Path | None = None,
    project_source_root: Path | None = None,
    contents_directory: str = "_internal",
    distribution_lookup: Callable[[Path], Iterable[DistributionCandidate]] | None = None,
) -> dict[str, object]:
    """Record per-file origin candidates without persisting absolute host paths."""
    toc_root = toc_path.parent.resolve(strict=True)
    raw_toc = _read_toc(toc_path)
    resolved_site_packages = (site_packages or Path(sysconfig.get_paths()["purelib"])).resolve()
    resolved_python_root = (python_root or Path(sys.base_prefix)).resolve()
    resolved_windows_root = (
        windows_root or Path(os.environ.get("SystemRoot", r"C:\Windows"))
    ).resolve()
    resolved_project_source_root = (
        project_source_root or ROOT / "src"
    ).resolve()
    candidates = list(
        (distribution_lookup or _installed_candidates)(resolved_site_packages)
    )
    contents_path = _normalized_bundle_path(contents_directory) if contents_directory else ""
    package_owners: dict[Path, list[DistributionCandidate]] = {}
    for candidate in candidates:
        for file_path in candidate.files:
            package_owners.setdefault(file_path.resolve(), []).append(candidate)
    pyinstaller = next(
        (candidate for candidate in candidates if candidate.name.casefold() == "pyinstaller"),
        None,
    )

    files: list[dict[str, object]] = []
    components: dict[str, dict[str, object]] = {}
    seen_bundle_paths: set[str] = set()
    for destination, source, kind in raw_toc:
        bundle_path = _normalized_bundle_path(destination)
        if kind != "EXECUTABLE" and contents_path:
            bundle_path = f"{contents_path}/{bundle_path}"
        folded_path = bundle_path.casefold()
        if folded_path in seen_bundle_paths:
            raise ValueError("O TOC contém destinos de bundle duplicados.")
        seen_bundle_paths.add(folded_path)

        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = toc_root / source_path
        source_path = source_path.resolve()
        origin = _classify_origin(
            source_path,
            site_packages=resolved_site_packages,
            python_root=resolved_python_root,
            windows_root=resolved_windows_root,
            project_source_root=resolved_project_source_root,
            build_root=toc_root,
            package_owners=package_owners,
            pyinstaller=pyinstaller,
        )
        file_record: dict[str, object] = {
            "bundle_path": bundle_path,
            "pyinstaller_kind": kind,
            "source_basename": source_path.name,
            **origin,
        }
        files.append(file_record)

        key = f"{origin['origin_status']}:{origin['component_name']}@{origin.get('version', '')}"
        component = components.setdefault(
            key,
            {
                "name": origin["component_name"],
                "version": origin.get("version"),
                "origin_status": origin["origin_status"],
                "source_root_kind": origin["source_root_kind"],
                "license_metadata_candidate": origin.get("license_metadata_candidate"),
                "license_file_path_candidates": origin.get("license_file_path_candidates", []),
                "project_url_candidate": origin.get("project_url_candidate"),
                "bundle_paths": [],
            },
        )
        bundle_paths = component["bundle_paths"]
        assert isinstance(bundle_paths, list)
        bundle_paths.append(bundle_path)

    unresolved_count = sum(
        str(file_record["origin_status"]).startswith("unresolved-")
        or file_record["origin_status"] == "ambiguous-package-owner"
        for file_record in files
    )
    return {
        "schema_version": "1.0",
        "evidence_kind": (
            "PyInstaller COLLECT TOC and installed distribution metadata; "
            "origin/license candidates, "
            "not legal approval"
        ),
        "build_toc_name": toc_path.name,
        "file_count": len(files),
        "mapped_file_count": len(files) - unresolved_count,
        "unresolved_file_count": unresolved_count,
        "provenance_status": "partial" if unresolved_count else "mapped",
        "license_review_status": "pending",
        "components": sorted(components.values(), key=lambda item: str(item["name"]).casefold()),
        "files": files,
        "scope_note": (
            "Source paths are classified and redacted; license metadata and license files are "
            "candidates only. Review notices and source terms before any release."
        ),
    }


def write_component_inventory(toc_path: Path, output_path: Path) -> dict[str, object]:
    inventory = build_component_inventory(toc_path)
    _write_inventory(inventory, output_path)
    return inventory


def _write_inventory(inventory: dict[str, object], output_path: Path) -> None:
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
            json.dump(inventory, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toc", type=Path, default=DEFAULT_TOC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contents-directory", default="_internal")
    args = parser.parse_args()
    inventory = build_component_inventory(
        args.toc,
        contents_directory=args.contents_directory,
    )
    _write_inventory(inventory, args.output)
    print(
        "Inventário de origem candidato gravado em: "
        f"{args.output} "
        f"({inventory['mapped_file_count']}/{inventory['file_count']} arquivos mapeados; "
        f"licenças {inventory['license_review_status']})"
    )
    return 0


def _read_toc(toc_path: Path) -> list[tuple[str, str, str]]:
    if _is_reparse_point(toc_path):
        raise ValueError("O TOC precisa ser arquivo regular, sem links.")
    try:
        value = ast.literal_eval(toc_path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError) as error:
        raise ValueError("O TOC de PyInstaller não é uma estrutura literal válida.") from error
    if not isinstance(value, tuple) or len(value) != 1 or not isinstance(value[0], list):
        raise ValueError("O TOC precisa ter a estrutura esperada do COLLECT PyInstaller.")
    rows: list[tuple[str, str, str]] = []
    for row in value[0]:
        if (
            not isinstance(row, tuple)
            or len(row) != 3
            or any(not isinstance(item, str) for item in row)
        ):
            raise ValueError("O TOC contém uma entrada de arquivo inválida.")
        rows.append((row[0], row[1], row[2]))
    if not rows:
        raise ValueError("O TOC não contém arquivos do bundle.")
    return rows


def _normalized_bundle_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(normalized)
    if (
        not normalized
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ":" in normalized
        or "\x00" in normalized
        or ".." in posix.parts
        or ".." in windows.parts
    ):
        raise ValueError("O TOC contém um destino inseguro no bundle.")
    return posix.as_posix()


def _installed_candidates(site_packages: Path) -> Iterable[DistributionCandidate]:
    for installed in distributions(path=[str(site_packages)]):
        name = installed.metadata.get("Name")
        if not name:
            continue
        version = installed.version
        license_metadata = _license_metadata(installed)
        license_paths = tuple(_license_file_paths(installed))
        files = tuple(
            Path(str(installed.locate_file(file))).resolve()
            for file in installed.files or ()
        )
        yield DistributionCandidate(
            name=name,
            version=version,
            project_url=f"https://pypi.org/project/{quote(name)}/{quote(version)}/",
            license_metadata=license_metadata,
            license_file_paths=license_paths,
            files=files,
        )


def _license_metadata(installed: Distribution) -> dict[str, object] | None:
    expression = installed.metadata.get("License-Expression")
    if expression:
        return {"field": "License-Expression", "value": expression}
    license_text = installed.metadata.get("License")
    if license_text:
        return {"field": "License", "value": license_text.strip()}
    classifiers = [
        classifier.removeprefix("License :: ")
        for classifier in installed.metadata.get_all("Classifier", [])
        if classifier.startswith("License ::")
    ]
    return {"field": "Classifier", "value": classifiers} if classifiers else None


def _license_file_paths(installed: Distribution) -> list[str]:
    paths = []
    for file in installed.files or ():
        path = PurePosixPath(str(file).replace("\\", "/"))
        if path.name.casefold().startswith(("license", "licence", "copying", "notice")):
            paths.append(path.as_posix())
    return sorted(paths, key=str.casefold)


def _classify_origin(
    source: Path,
    *,
    site_packages: Path,
    python_root: Path,
    windows_root: Path,
    project_source_root: Path,
    build_root: Path,
    package_owners: dict[Path, list[DistributionCandidate]],
    pyinstaller: DistributionCandidate | None,
) -> dict[str, object]:
    if source in package_owners:
        owners = package_owners[source]
        if len(owners) != 1:
            return {
                "origin_status": "ambiguous-package-owner",
                "source_root_kind": "python-site-packages",
                "component_name": source.name,
                "source_basename": source.name,
            }
        candidate = owners[0]
        return _candidate_origin(candidate, "distribution-metadata-match")
    if _is_within(source, site_packages):
        return {
            "origin_status": "unresolved-site-package-file",
            "source_root_kind": "python-site-packages",
            "component_name": source.name,
            "source_basename": source.name,
        }
    if _is_within(source, project_source_root):
        return {
            "origin_status": "application-source",
            "source_root_kind": "project-source",
            "component_name": "Manga to Kindle application",
            "source_basename": source.name,
        }
    if _is_within(source, build_root):
        if pyinstaller is not None:
            return _candidate_origin(pyinstaller, "pyinstaller-build-output")
        return {
            "origin_status": "pyinstaller-build-output",
            "source_root_kind": "pyinstaller-build",
            "component_name": "PyInstaller-generated build output",
            "source_basename": source.name,
        }
    if _is_within(source, python_root):
        return {
            "origin_status": "python-runtime-path",
            "source_root_kind": "python-runtime",
            "component_name": "Python runtime",
            "version": sys.version.split()[0],
            "source_basename": source.name,
        }
    if _is_within(source, windows_root):
        return {
            "origin_status": "windows-system-path",
            "source_root_kind": "windows-system",
            "component_name": "Windows system component",
            "source_basename": source.name,
        }
    if source.name.casefold().startswith(("api-ms-win-", "ext-ms-win-")):
        return {
            "origin_status": "windows-api-set",
            "source_root_kind": "windows-loader-contract",
            "component_name": "Windows API set",
            "source_basename": source.name,
        }
    return {
        "origin_status": "unresolved-external",
        "source_root_kind": "unresolved-external",
        "component_name": f"Unresolved origin: {source.name}",
        "source_basename": source.name,
    }


def _candidate_origin(
    candidate: DistributionCandidate, origin_status: str
) -> dict[str, object]:
    return {
        "origin_status": origin_status,
        "source_root_kind": "python-package",
        "component_name": candidate.name,
        "version": candidate.version,
        "project_url_candidate": candidate.project_url,
        "license_metadata_candidate": candidate.license_metadata,
        "license_file_path_candidates": list(candidate.license_file_paths),
    }


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_reparse_point(path: Path) -> bool:
    metadata = path.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_attribute
    )


if __name__ == "__main__":
    raise SystemExit(main())
