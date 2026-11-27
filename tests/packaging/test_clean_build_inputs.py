from __future__ import annotations

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_build_inputs_are_locked_and_pyinstaller_is_pinned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    build_group = project["dependency-groups"]["build"]
    third_party_notices = ROOT / "packaging" / "third-party-notices"

    assert (ROOT / "uv.lock").is_file()
    assert any(requirement == "pyinstaller==6.22.3" for requirement in build_group)
    assert (ROOT / "packaging" / "pyinstaller" / "MangaToKindle.spec").is_file()
    assert (ROOT / "packaging" / "windows" / "version-info.txt").is_file()
    assert (ROOT / "packaging" / "windows" / "manga_to_kindle.ico").is_file()
    assert (third_party_notices / "dependency-inventory.cdx.json").is_file()
    assert (third_party_notices / "dependency-license-candidates.json").is_file()
    assert (third_party_notices / "bundle-file-inventory.json").is_file()
    assert (ROOT / "tools" / "release" / "license_inventory.py").is_file()
    assert (ROOT / "tools" / "release" / "bundle_inventory.py").is_file()

    spec_tree = ast.parse(
        (ROOT / "packaging" / "pyinstaller" / "MangaToKindle.spec").read_text(
            encoding="utf-8"
        )
    )
    analysis = next(
        node
        for node in ast.walk(spec_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Analysis"
    )
    excludes = next(
        ast.literal_eval(keyword.value)
        for keyword in analysis.keywords
        if keyword.arg == "excludes"
    )
    assert {
        "mypy",
        "mypy_extensions",
        "pydantic.mypy",
        "pydantic.v1.mypy",
        "setuptools",
        "pkg_resources",
    }.issubset(excludes)
