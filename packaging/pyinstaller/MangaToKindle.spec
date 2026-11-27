# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[1]
migration_directory = (
    project_root
    / "src"
    / "manga_to_kindle"
    / "infrastructure"
    / "persistence"
    / "migrations"
)
migration_data = [
    (
        str(path),
        (
            Path("manga_to_kindle/infrastructure/persistence/migrations")
            / path.relative_to(migration_directory).parent
        ).as_posix(),
    )
    for path in migration_directory.rglob("*.py")
]

a = Analysis(
    [str(project_root / "src" / "manga_to_kindle" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=migration_data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "mypy",
        "mypy_extensions",
        "pydantic.mypy",
        "pydantic.v1.mypy",
        "setuptools",
        "pkg_resources",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MangaToKindle",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    contents_directory="_internal",
    codesign_identity=None,
    entitlements_file=None,
    version=str(project_root / "packaging" / "windows" / "version-info.txt"),
    icon=[str(project_root / "packaging" / "windows" / "manga_to_kindle.ico")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MangaToKindle",
)
