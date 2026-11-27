"""Create a path-and-hash inventory of the actual PyInstaller onedir bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
DEFAULT_BUNDLE = ROOT / "dist" / "MangaToKindle"
DEFAULT_OUTPUT = ROOT / "packaging" / "third-party-notices" / "bundle-file-inventory.json"


def build_bundle_inventory(bundle_path: Path) -> dict[str, Any]:
    """Hash every regular file in a bundle without inferring provenance or licenses."""
    if _is_reparse_point(bundle_path):
        raise ValueError("O diretório do bundle precisa existir e não pode ser link.")
    root = bundle_path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("O diretório do bundle precisa existir e não pode ser link.")

    files: list[dict[str, object]] = []
    total_size = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if _is_reparse_point(path):
            raise ValueError("O bundle não pode conter links ou pontos de nova análise.")
        if not path.is_file():
            continue

        relative_path = path.relative_to(root).as_posix()
        if relative_path.startswith("/") or ".." in Path(relative_path).parts:
            raise ValueError("O bundle contém um caminho relativo inseguro.")
        size_bytes = path.stat().st_size
        total_size += size_bytes
        files.append(
            {
                "path": relative_path,
                "size_bytes": size_bytes,
                "sha256": _sha256(path),
            }
        )

    if not files:
        raise ValueError("O diretório do bundle não contém arquivos para inventariar.")

    return {
        "schema_version": "1.0",
        "bundle_directory": root.name,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "license_review_status": "pending",
        "scope_note": (
            "Inventário de arquivos e hashes do bundle; não identifica origem, componente "
            "nem licença. A revisão dos componentes continua pendente."
        ),
        "files": files,
    }


def write_bundle_inventory(bundle_path: Path, output_path: Path) -> None:
    inventory = build_bundle_inventory(bundle_path)
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
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_bundle_inventory(args.bundle, args.output)
    print(f"Inventário do bundle gravado em: {args.output}")
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_reparse_point(path: Path) -> bool:
    metadata = path.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_attribute
    )


if __name__ == "__main__":
    raise SystemExit(main())
