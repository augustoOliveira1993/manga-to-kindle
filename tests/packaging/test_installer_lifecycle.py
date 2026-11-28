from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
import zipfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).parents[2]
INSTALLER = ROOT / "packaging" / "installer" / "Install-MangaToKindle.ps1"
UNINSTALLER = ROOT / "packaging" / "installer" / "Uninstall-MangaToKindle.ps1"
POWERSHELL = shutil.which("powershell.exe")


def _run_powershell(
    script: Path,
    *arguments: str,
    env: Mapping[str, str],
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        input=input_text,
        timeout=30,
    )


def _start_bundle_and_wait_for_latest_migration(
    executable: Path, data_root: Path, environment: Mapping[str, str]
) -> Path:
    app_environment = dict(environment)
    app_environment["QT_QPA_PLATFORM"] = "offscreen"
    app_environment["MANGA_TO_KINDLE_DATA_ROOT"] = str(data_root)
    process = subprocess.Popen([str(executable)], env=app_environment)
    database = data_root / "data" / "manga_to_kindle.sqlite3"
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise AssertionError(
                    f"O aplicativo encerrou durante o startup (code {process.returncode})."
                )
            if database.is_file():
                escaped_path = quote(str(database).replace("\\", "/"), safe="/:")
                try:
                    with sqlite3.connect(f"file:{escaped_path}?mode=ro", uri=True) as connection:
                        row = connection.execute(
                            "SELECT version_num FROM alembic_version"
                        ).fetchone()
                except sqlite3.Error:
                    row = None
                if row == ("0011_mobi_export_artifacts",):
                    return database
            time.sleep(0.1)
        raise AssertionError("O aplicativo não concluiu o startup no perfil local isolado.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.skipif(
    os.name != "nt" or POWERSHELL is None,
    reason="Validação usa PowerShell do Windows",
)
def test_install_and_uninstall_preserve_user_data_and_cancel_safely(tmp_path: Path) -> None:
    local_app_data = tmp_path / "LocalAppData"
    app_data = tmp_path / "AppData" / "Roaming"
    shortcut_directory = tmp_path / "StartMenu"
    install_directory = local_app_data / "Programs" / "MangaToKindle"
    user_data = local_app_data / "MangaToKindle" / "MangaToKindle" / "data"
    user_data.mkdir(parents=True)
    app_data.mkdir(parents=True)
    database_sentinel = user_data / "library.sqlite3"
    database_sentinel.write_bytes(b"existing-user-library")
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("MangaToKindle.exe", b"test-bundle-marker")
        bundle.writestr("_internal/runtime.dat", b"runtime")

    registry_path = f"HKCU:\\Software\\MangaToKindleInstallerTests\\{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(local_app_data)
    environment["APPDATA"] = str(app_data)

    installed = _run_powershell(
        INSTALLER,
        "-ArchivePath",
        str(archive),
        "-InstallDirectory",
        str(install_directory),
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmInstall",
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    marker = json.loads(
        (install_directory / "manga-to-kindle.install.json").read_text(encoding="utf-8-sig")
    )
    assert marker["product_id"] == "manga-to-kindle"
    assert (shortcut_directory / "Manga to Kindle.lnk").is_file()
    assert database_sentinel.read_bytes() == b"existing-user-library"
    assert not (install_directory / "data").exists()

    cancelled = _run_powershell(
        UNINSTALLER,
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        env=environment,
        input_text="NAO\n",
    )
    assert cancelled.returncode == 0, cancelled.stdout + cancelled.stderr
    assert install_directory.is_dir()

    removed = _run_powershell(
        UNINSTALLER,
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmUninstall",
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not install_directory.exists()
    assert database_sentinel.read_bytes() == b"existing-user-library"
    assert not (shortcut_directory / "Manga to Kindle.lnk").exists()


@pytest.mark.skipif(
    os.name != "nt" or POWERSHELL is None,
    reason="Validação usa PowerShell do Windows",
)
def test_installer_rejects_zip_path_traversal(tmp_path: Path) -> None:
    local_app_data = tmp_path / "LocalAppData"
    app_data = tmp_path / "AppData" / "Roaming"
    install_directory = local_app_data / "Programs" / "MangaToKindle"
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("MangaToKindle.exe", b"test-bundle-marker")
        bundle.writestr("../outside.txt", b"must-not-extract")

    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(local_app_data)
    environment["APPDATA"] = str(app_data)
    result = _run_powershell(
        INSTALLER,
        "-ArchivePath",
        str(archive),
        "-InstallDirectory",
        str(install_directory),
        "-ConfirmInstall",
        env=environment,
    )

    assert result.returncode != 0
    assert not (tmp_path / "outside.txt").exists()
    assert not install_directory.exists()


@pytest.mark.skipif(
    os.name != "nt" or POWERSHELL is None,
    reason="Validação usa PowerShell do Windows",
)
def test_update_preserves_previous_install_and_user_data(tmp_path: Path) -> None:
    local_app_data = tmp_path / "LocalAppData"
    app_data = tmp_path / "AppData" / "Roaming"
    shortcut_directory = tmp_path / "StartMenu"
    install_directory = local_app_data / "Programs" / "MangaToKindle"
    user_data = local_app_data / "MangaToKindle" / "MangaToKindle" / "data"
    user_data.mkdir(parents=True)
    app_data.mkdir(parents=True)
    database_sentinel = user_data / "library.sqlite3"
    database_sentinel.write_bytes(b"existing-user-library")
    old_archive = tmp_path / "old-bundle.zip"
    new_archive = tmp_path / "new-bundle.zip"
    rollback_archive = tmp_path / "rollback-bundle.zip"
    invalid_archive = tmp_path / "invalid-bundle.zip"
    with zipfile.ZipFile(old_archive, "w") as bundle:
        bundle.writestr("MangaToKindle.exe", b"old-bundle")
    with zipfile.ZipFile(new_archive, "w") as bundle:
        bundle.writestr("MangaToKindle.exe", b"new-bundle")
    with zipfile.ZipFile(rollback_archive, "w") as bundle:
        bundle.writestr("MangaToKindle.exe", b"rollback-bundle")
    invalid_archive.write_bytes(b"not-a-zip")

    registry_path = f"HKCU:\\Software\\MangaToKindleInstallerTests\\{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(local_app_data)
    environment["APPDATA"] = str(app_data)

    for archive in (old_archive, new_archive):
        installed = _run_powershell(
            INSTALLER,
            "-ArchivePath",
            str(archive),
            "-InstallDirectory",
            str(install_directory),
            "-RegistryPath",
            registry_path,
            "-ShortcutDirectory",
            str(shortcut_directory),
            "-ConfirmInstall",
            env=environment,
        )
        assert installed.returncode == 0, installed.stdout + installed.stderr

    previous_installations = list(install_directory.parent.glob("MangaToKindle.previous-*"))
    assert len(previous_installations) == 1
    assert (previous_installations[0] / "MangaToKindle.exe").read_bytes() == b"old-bundle"
    assert (install_directory / "MangaToKindle.exe").read_bytes() == b"new-bundle"
    assert database_sentinel.read_bytes() == b"existing-user-library"

    blocked_shortcut_directory = tmp_path / "blocked-shortcuts"
    blocked_shortcut_directory.write_text("not a directory", encoding="utf-8")
    failed_after_publish = _run_powershell(
        INSTALLER,
        "-ArchivePath",
        str(rollback_archive),
        "-InstallDirectory",
        str(install_directory),
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(blocked_shortcut_directory),
        "-ConfirmInstall",
        env=environment,
    )
    assert failed_after_publish.returncode != 0
    assert (install_directory / "MangaToKindle.exe").read_bytes() == b"new-bundle"
    failed_installations = list(install_directory.parent.glob("MangaToKindle.failed-*"))
    assert len(failed_installations) == 1
    assert (failed_installations[0] / "MangaToKindle.exe").read_bytes() == b"rollback-bundle"
    assert database_sentinel.read_bytes() == b"existing-user-library"

    failed_update = _run_powershell(
        INSTALLER,
        "-ArchivePath",
        str(invalid_archive),
        "-InstallDirectory",
        str(install_directory),
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmInstall",
        env=environment,
    )
    assert failed_update.returncode != 0
    assert (install_directory / "MangaToKindle.exe").read_bytes() == b"new-bundle"
    assert database_sentinel.read_bytes() == b"existing-user-library"

    removed = _run_powershell(
        UNINSTALLER,
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmUninstall",
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not install_directory.exists()
    assert database_sentinel.read_bytes() == b"existing-user-library"


@pytest.mark.skipif(
    os.name != "nt" or POWERSHELL is None,
    reason="Validação usa PowerShell do Windows",
)
def test_bundle_starts_and_applies_latest_migration_in_an_isolated_profile(tmp_path: Path) -> None:
    executable = ROOT / "dist" / "MangaToKindle" / "MangaToKindle.exe"
    if not executable.is_file():
        pytest.skip("Execute o build PyInstaller antes do smoke test do bundle")
    assert not (executable.parent / "_internal" / "mypy").exists()
    assert not (executable.parent / "_internal" / "setuptools").exists()
    assert not (executable.parent / "_internal" / "pkg_resources").exists()

    local_app_data = tmp_path / "LocalAppData"
    app_data = tmp_path / "AppData" / "Roaming"
    local_app_data.mkdir()
    app_data.mkdir(parents=True)
    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(local_app_data)
    environment["APPDATA"] = str(app_data)
    isolated_profile = tmp_path / "isolated-profile"
    database = _start_bundle_and_wait_for_latest_migration(
        executable, isolated_profile, environment
    )
    assert database.is_file()


@pytest.mark.skipif(
    os.name != "nt" or POWERSHELL is None,
    reason="Validação usa PowerShell do Windows",
)
def test_local_archive_installs_starts_and_uninstalls_without_removing_user_data(
    tmp_path: Path,
) -> None:
    draft_directory = ROOT / "dist" / "local-release-draft"
    archives = sorted(
        draft_directory.glob("MangaToKindle-0.1.0-windows-x64-local-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not archives:
        pytest.skip("Execute o empacotador local antes do teste end-to-end de distribuição")
    archive = archives[0]
    assert (draft_directory / "dependency-inventory.cdx.json").is_file()
    license_candidates = json.loads(
        (draft_directory / "dependency-license-candidates.json").read_text(encoding="utf-8")
    )
    assert license_candidates["evidence_kind"] == "package metadata candidates; not legal approval"
    bundle_inventory = json.loads(
        (draft_directory / "bundle-file-inventory.json").read_text(encoding="utf-8")
    )
    assert bundle_inventory["file_count"] > 0
    assert bundle_inventory["license_review_status"] == "pending"

    local_app_data = tmp_path / "L"
    app_data = tmp_path / "AppData" / "Roaming"
    shortcut_directory = tmp_path / "StartMenu"
    install_directory = local_app_data / "I"
    data_root = tmp_path / "isolated-user-data"
    data_root.mkdir()
    app_data.mkdir(parents=True)
    sentinel = data_root / "user-data-sentinel.txt"
    sentinel.write_text("preservar dados locais", encoding="utf-8")
    registry_path = f"HKCU:\\Software\\MangaToKindleInstallerTests\\{uuid.uuid4().hex}"
    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(local_app_data)
    environment["APPDATA"] = str(app_data)

    installed = _run_powershell(
        draft_directory / "Install-MangaToKindle.ps1",
        "-ArchivePath",
        str(archive),
        "-InstallDirectory",
        str(install_directory),
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmInstall",
        env=environment,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr

    database = _start_bundle_and_wait_for_latest_migration(
        install_directory / "MangaToKindle.exe", data_root, environment
    )
    database_hash_before_update = hashlib.sha256(database.read_bytes()).hexdigest()

    updated = _run_powershell(
        draft_directory / "Install-MangaToKindle.ps1",
        "-ArchivePath",
        str(archive),
        "-InstallDirectory",
        str(install_directory),
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmInstall",
        env=environment,
    )
    assert updated.returncode == 0, updated.stdout + updated.stderr
    assert hashlib.sha256(database.read_bytes()).hexdigest() == database_hash_before_update
    assert list(install_directory.parent.glob("MangaToKindle.previous-*"))
    database = _start_bundle_and_wait_for_latest_migration(
        install_directory / "MangaToKindle.exe", data_root, environment
    )
    assert database.is_file()

    removed = _run_powershell(
        install_directory / "Uninstall-MangaToKindle.ps1",
        "-RegistryPath",
        registry_path,
        "-ShortcutDirectory",
        str(shortcut_directory),
        "-ConfirmUninstall",
        env=environment,
    )
    assert removed.returncode == 0, removed.stdout + removed.stderr
    assert not install_directory.exists()
    assert sentinel.read_text(encoding="utf-8") == "preservar dados locais"
    assert database.is_file()
