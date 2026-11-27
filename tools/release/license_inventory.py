"""Build a traceable list of declared package-license metadata for release review."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path, PurePosixPath
from urllib.parse import quote


def build_license_inventory(
    sbom_path: Path,
    distribution_lookup: Callable[[str], Distribution] = distribution,
) -> dict[str, object]:
    """Match CycloneDX package versions to installed metadata without approving licenses."""
    sbom_bytes = sbom_path.read_bytes()
    sbom: object = json.loads(sbom_bytes.decode("utf-8"))
    if not isinstance(sbom, dict) or not isinstance(sbom.get("components"), list):
        raise ValueError("O SBOM precisa conter uma lista de componentes.")

    components: list[dict[str, object]] = []
    for raw_component in sbom["components"]:
        if not isinstance(raw_component, dict):
            raise ValueError("O SBOM contém um componente inválido.")
        name = raw_component.get("name")
        version = raw_component.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise ValueError("Cada componente precisa declarar nome e versão.")

        item: dict[str, object] = {
            "name": name,
            "version": version,
            "pypi_project_version": (
                f"https://pypi.org/project/{quote(name)}/{quote(version)}/"
            ),
            "license_review_status": "pending",
        }
        try:
            installed = distribution_lookup(name)
        except PackageNotFoundError:
            item["metadata_status"] = "not-installed-on-build-host"
            item["declared_license_metadata"] = None
            item["license_file_paths"] = []
        else:
            installed_version = installed.version
            if installed_version != version:
                item["metadata_status"] = "version-mismatch"
                item["installed_version"] = installed_version
                item["declared_license_metadata"] = None
                item["license_file_paths"] = []
            else:
                item["metadata_status"] = "matched-installed-distribution"
                item["declared_license_metadata"] = _declared_license(installed)
                item["license_file_paths"] = _license_files(installed)
                item["upstream_urls"] = _upstream_urls(installed)
        components.append(item)

    components.sort(key=lambda component: str(component["name"]).casefold())
    return {
        "schema_version": "1.0",
        "evidence_kind": "package metadata candidates; not legal approval",
        "source_sbom": sbom_path.name,
        "source_sbom_sha256": hashlib.sha256(sbom_bytes).hexdigest(),
        "components": components,
    }


def write_license_inventory(sbom_path: Path, output_path: Path) -> None:
    inventory = build_license_inventory(sbom_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _declared_license(installed: Distribution) -> dict[str, object] | None:
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
    if classifiers:
        return {"field": "Classifier", "value": classifiers}
    return None


def _license_files(installed: Distribution) -> list[str]:
    candidates = installed.files or ()
    selected: set[str] = set()
    for candidate in candidates:
        relative_path = PurePosixPath(str(candidate).replace("\\", "/"))
        filename = relative_path.name.casefold()
        if filename.startswith(("license", "licence", "copying", "notice")):
            selected.add(relative_path.as_posix())
    return sorted(selected, key=str.casefold)


def _upstream_urls(installed: Distribution) -> list[dict[str, str]]:
    urls: set[tuple[str, str]] = set()
    for project_url in installed.metadata.get_all("Project-URL", []):
        label, separator, url = project_url.partition(",")
        if separator and url.strip().startswith(("https://", "http://")):
            urls.add((label.strip(), url.strip()))
    homepage = installed.metadata.get("Home-page")
    if homepage and homepage.startswith(("https://", "http://")):
        urls.add(("Home-page", homepage))
    return [{"label": label, "url": url} for label, url in sorted(urls)]


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[2]
    notices_directory = repository_root / "packaging" / "third-party-notices"
    write_license_inventory(
        notices_directory / "dependency-inventory.cdx.json",
        notices_directory / "dependency-license-candidates.json",
    )
