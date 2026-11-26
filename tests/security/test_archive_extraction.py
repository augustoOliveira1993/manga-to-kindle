from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from tests.image_support import FIXTURES

from manga_to_kindle.application.images.errors import ImageLimitExceeded, ImageSourceRejected
from manga_to_kindle.application.images.import_source import ScanImageSource
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader


@pytest.mark.parametrize(
    "archive_name",
    ("traversal.cbz", "case-collision.cbz", "symlink.cbz"),
)
def test_unsafe_cbz_entries_reject_the_whole_archive(archive_name: str) -> None:
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageSourceRejected):
        scan.execute(FIXTURES / archive_name)


def test_valid_cbz_uses_safe_member_names_and_natural_order() -> None:
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    plan = scan.execute(FIXTURES / "valid.cbz")

    assert plan.source_kind.value == "cbz"
    assert [image.relative_path for image in plan.images] == [
        "capitulo/pagina_1.png",
        "capitulo/pagina_2.jpg",
        "capitulo/pagina_10.webp",
    ]
    assert plan.ignored_entries == 1


def test_encrypted_archive_is_rejected_from_header_bits(tmp_path: Path) -> None:
    archive_path = tmp_path / "criptografado.cbz"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("pagina.png", (FIXTURES / "valid" / "pagina_1.png").read_bytes())
    contents = bytearray(archive_path.read_bytes())
    _set_zip_flag(contents, b"PK\x03\x04", 6)
    _set_zip_flag(contents, b"PK\x01\x02", 8)
    archive_path.write_bytes(contents)
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageSourceRejected, match="senha"):
        scan.execute(archive_path)


def test_directory_symlinks_are_ignored_without_following_them(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leak.png").write_bytes((FIXTURES / "valid" / "pagina_1.png").read_bytes())
    try:
        os.symlink(outside, source / "atalho", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("O ambiente não permite criar links simbólicos para este teste.")
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageSourceRejected, match="não contém imagens"):
        scan.execute(source)


def test_entry_count_limit_stops_large_archives_before_read(tmp_path: Path) -> None:
    archive_path = tmp_path / "muitas-entradas.cbz"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as archive:
        for index in range(10_001):
            archive.writestr(f"notas/{index}.txt", b"x")
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageLimitExceeded, match="10.000"):
        scan.execute(archive_path)


def _set_zip_flag(data: bytearray, signature: bytes, flag_offset: int) -> None:
    cursor = 0
    while True:
        position = data.find(signature, cursor)
        if position < 0:
            return
        flag_index = position + flag_offset
        flags = int.from_bytes(data[flag_index : flag_index + 2], "little")
        data[flag_index : flag_index + 2] = (flags | 1).to_bytes(2, "little")
        cursor = flag_index + 2
