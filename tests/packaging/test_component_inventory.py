from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.release.component_inventory import (
    DistributionCandidate,
    build_component_inventory,
    write_component_inventory,
)


def test_component_inventory_maps_bundle_paths_and_redacts_source_paths(
    tmp_path: Path,
) -> None:
    build_root = tmp_path / "build"
    build_root.mkdir()
    project_source = tmp_path / "src"
    project_source.mkdir()
    site_packages = tmp_path / "site-packages"
    package_file = site_packages / "sample_package" / "__init__.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("package", encoding="utf-8")
    python_root = tmp_path / "python"
    python_root.mkdir()
    windows_root = tmp_path / "windows"
    windows_root.mkdir()
    external_root = tmp_path / "external-runtime"
    external_root.mkdir()

    app_source = project_source / "main.py"
    app_source.write_text("application", encoding="utf-8")
    executable = build_root / "MangaToKindle.exe"
    executable.write_bytes(b"exe")
    runtime = python_root / "python312.dll"
    runtime.write_bytes(b"python runtime")
    system_dll = windows_root / "kernel32.dll"
    system_dll.write_bytes(b"windows")
    api_set = external_root / "api-ms-win-core-test-l1-1-0.dll"
    api_set.write_bytes(b"api set")
    unresolved = external_root / "ucrtbase.dll"
    unresolved.write_bytes(b"unknown runtime")
    toc = build_root / "COLLECT-00.toc"
    rows = [
        ("MangaToKindle.exe", str(executable), "EXECUTABLE"),
        ("manga_to_kindle/main.py", str(app_source), "DATA"),
        ("sample_package/__init__.py", str(package_file), "DATA"),
        ("python312.dll", str(runtime), "BINARY"),
        ("kernel32.dll", str(system_dll), "BINARY"),
        (api_set.name, str(api_set), "BINARY"),
        ("ucrtbase.dll", str(unresolved), "BINARY"),
    ]
    toc.write_text(repr((rows,)), encoding="utf-8")
    distribution = DistributionCandidate(
        name="sample-package",
        version="1.2.3",
        project_url="https://pypi.org/project/sample-package/1.2.3/",
        license_metadata={"field": "License-Expression", "value": "MIT"},
        license_file_paths=("sample_package-1.2.3.dist-info/licenses/LICENSE.txt",),
        files=(package_file,),
    )

    inventory = build_component_inventory(
        toc,
        site_packages=site_packages,
        python_root=python_root,
        windows_root=windows_root,
        project_source_root=project_source,
        distribution_lookup=lambda _root: (distribution,),
    )

    assert inventory["file_count"] == len(rows)
    assert inventory["unresolved_file_count"] == 1
    assert inventory["provenance_status"] == "partial"
    assert inventory["license_review_status"] == "pending"
    files = inventory["files"]
    assert isinstance(files, list)
    by_name = {record["source_basename"]: record for record in files}
    assert by_name["main.py"]["origin_status"] == "application-source"
    assert by_name["__init__.py"]["component_name"] == "sample-package"
    assert by_name["python312.dll"]["origin_status"] == "python-runtime-path"
    assert by_name["kernel32.dll"]["origin_status"] == "windows-system-path"
    assert by_name[api_set.name]["origin_status"] == "windows-api-set"
    assert by_name["ucrtbase.dll"]["origin_status"] == "unresolved-external"
    assert {record["bundle_path"] for record in files} == {
        "MangaToKindle.exe",
        "_internal/manga_to_kindle/main.py",
        "_internal/sample_package/__init__.py",
        "_internal/python312.dll",
        "_internal/kernel32.dll",
        f"_internal/{api_set.name}",
        "_internal/ucrtbase.dll",
    }
    assert str(tmp_path).casefold() not in json.dumps(inventory).casefold()

    output = tmp_path / "evidence" / "components.json"
    written_inventory = write_component_inventory(toc, output)
    assert json.loads(output.read_text(encoding="utf-8")) == written_inventory
    assert not list(output.parent.glob("*.tmp"))


@pytest.mark.parametrize(
    "destination",
    ["../outside.dll", "C:/outside.dll", "\\\\server\\share.dll"],
)
def test_component_inventory_rejects_unsafe_bundle_destinations(
    tmp_path: Path, destination: str
) -> None:
    build_root = tmp_path / "build"
    build_root.mkdir()
    source = tmp_path / "source.dll"
    source.write_bytes(b"data")
    toc = build_root / "COLLECT-00.toc"
    toc.write_text(repr(([(destination, str(source), "BINARY")],)), encoding="utf-8")

    with pytest.raises(ValueError, match="destino inseguro"):
        build_component_inventory(
            toc,
            distribution_lookup=lambda _root: (),
        )
