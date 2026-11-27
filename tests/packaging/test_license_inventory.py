from __future__ import annotations

import json
from pathlib import Path

from tools.release.license_inventory import build_license_inventory

ROOT = Path(__file__).parents[2]


def test_license_inventory_covers_sbom_components_and_keeps_review_pending() -> None:
    sbom_path = ROOT / "packaging" / "third-party-notices" / "dependency-inventory.cdx.json"
    expected_sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    inventory = build_license_inventory(sbom_path)
    components = inventory["components"]

    assert isinstance(components, list)
    assert len(components) == len(expected_sbom["components"])
    assert len(inventory["source_sbom_sha256"]) == 64
    assert {component["name"] for component in components} == {
        component["name"] for component in expected_sbom["components"]
    }
    assert all(component["license_review_status"] == "pending" for component in components)
    assert all(
        component["pypi_project_version"].startswith("https://pypi.org/")
        for component in components
    )


def test_license_inventory_does_not_use_metadata_from_a_different_version(tmp_path: Path) -> None:
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(
        json.dumps(
            {
                "components": [
                    {"name": "sample-package", "version": "1.0.0"},
                ]
            }
        ),
        encoding="utf-8",
    )

    class InstalledDistribution:
        version = "2.0.0"

        @property
        def metadata(self) -> dict[str, str]:
            return {"License-Expression": "MIT"}

        @property
        def files(self) -> list[str]:
            return ["sample_package-2.0.0.dist-info/licenses/LICENSE"]

    inventory = build_license_inventory(sbom_path, lambda _: InstalledDistribution())  # type: ignore[arg-type]
    component = inventory["components"][0]

    assert component["metadata_status"] == "version-mismatch"
    assert component["installed_version"] == "2.0.0"
    assert component["declared_license_metadata"] is None
    assert component["license_file_paths"] == []
