from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
UV = shutil.which("uv")


@pytest.mark.release
@pytest.mark.skipif(os.name != "nt", reason="O bundle PyInstaller desta feature é Windows.")
@pytest.mark.skipif(UV is None, reason="uv precisa estar disponível no PATH.")
@pytest.mark.skipif(
    os.environ.get("M2K_RUN_CLEAN_BUILD_TEST") != "1",
    reason="Defina M2K_RUN_CLEAN_BUILD_TEST=1 para executar o build isolado.",
)
def test_release_bundle_builds_from_a_clean_source_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()

    for filename in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copy2(ROOT / filename, snapshot / filename)

    for directory in ("src", "packaging/pyinstaller", "packaging/windows"):
        source = ROOT / directory
        destination = snapshot / directory
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    tools_directory = snapshot / "tools" / "release"
    tools_directory.mkdir(parents=True)
    for filename in (
        "__init__.py",
        "bundle_inventory.py",
        "component_inventory.py",
    ):
        shutil.copy2(ROOT / "tools" / "release" / filename, tools_directory / filename)

    assert not (snapshot / ".git").exists()
    assert not (snapshot / ".venv").exists()
    assert not (snapshot / "dist").exists()
    assert not (snapshot / "build").exists()

    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    for variable in (
        "PYTHONHOME",
        "PYTHONPATH",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
    ):
        environment.pop(variable, None)
    environment["UV_PROJECT_ENVIRONMENT"] = str(snapshot / ".venv")
    windows_root = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(
        str(path)
        for path in (
            snapshot / ".venv" / "Scripts",
            windows_root / "System32",
            windows_root,
            windows_root / "System32" / "Wbem",
            windows_root / "System32" / "WindowsPowerShell" / "v1.0",
        )
    )

    _run_build_command(
        [
            UV or "uv",
            "sync",
            "--locked",
            "--python",
            "3.12",
            "--no-default-groups",
            "--group",
            "build",
        ],
        snapshot,
        environment,
    )
    _run_build_command(
        [
            UV or "uv",
            "run",
            "--locked",
            "--python",
            "3.12",
            "--no-default-groups",
            "--group",
            "build",
            "pyinstaller",
            "--clean",
            "--noconfirm",
            "packaging/pyinstaller/MangaToKindle.spec",
        ],
        snapshot,
        environment,
    )

    toc_path = snapshot / "build" / "MangaToKindle" / "COLLECT-00.toc"
    bundle_path = snapshot / "dist" / "MangaToKindle"
    component_inventory_path = snapshot / "component-candidates.json"
    bundle_inventory_path = snapshot / "bundle-inventory.json"
    for command in (
        [
            UV or "uv",
            "run",
            "--locked",
            "--python",
            "3.12",
            "--no-default-groups",
            "--group",
            "build",
            "python",
            "-m",
            "tools.release.component_inventory",
            "--toc",
            str(toc_path),
            "--output",
            str(component_inventory_path),
        ],
        [
            UV or "uv",
            "run",
            "--locked",
            "--python",
            "3.12",
            "--no-default-groups",
            "--group",
            "build",
            "python",
            "-m",
            "tools.release.bundle_inventory",
            "--bundle",
            str(bundle_path),
            "--output",
            str(bundle_inventory_path),
        ],
    ):
        _run_build_command(command, snapshot, environment)

    executable = snapshot / "dist" / "MangaToKindle" / "MangaToKindle.exe"
    assert executable.is_file()
    assert executable.stat().st_size > 0
    component_inventory = json.loads(component_inventory_path.read_text(encoding="utf-8"))
    bundle_inventory = json.loads(bundle_inventory_path.read_text(encoding="utf-8"))
    assert component_inventory["unresolved_file_count"] == 0
    assert component_inventory["license_review_status"] == "pending"
    assert component_inventory["file_count"] == bundle_inventory["file_count"]
    assert {
        item["bundle_path"] for item in component_inventory["files"]
    } == {item["path"] for item in bundle_inventory["files"]}
    assert str(snapshot).casefold() not in component_inventory_path.read_text(
        encoding="utf-8"
    ).casefold()


def _run_build_command(
    command: list[str], working_directory: Path, environment: dict[str, str]
) -> None:
    result = subprocess.run(
        command,
        cwd=working_directory,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Comando de build falhou ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout[-6000:]}\n"
            f"stderr:\n{result.stderr[-6000:]}"
        )
