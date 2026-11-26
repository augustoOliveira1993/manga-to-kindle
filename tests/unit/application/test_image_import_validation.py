from __future__ import annotations

from pathlib import Path

import pytest
from tests.image_support import FIXTURES

from manga_to_kindle.application.images.errors import (
    ImageContentRejected,
    ImageLimitExceeded,
)
from manga_to_kindle.application.images.import_source import (
    ScanImageSource,
    natural_sort_key,
    order_image_paths,
)
from manga_to_kindle.domain.image_processing import (
    ImageSourceFile,
    ImageSourceKind,
)
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader


def test_natural_order_uses_numbers_and_stable_case_tiebreaks() -> None:
    paths = ("pagina10.png", "Pagina2.png", "pagina01.png", "pagina1.png")

    expected = ("pagina01.png", "pagina1.png", "Pagina2.png", "pagina10.png")
    assert order_image_paths(paths) == expected
    assert natural_sort_key("pagina2.png") < natural_sort_key("pagina10.png")


def test_scan_folder_recognizes_formats_ignores_other_files_and_sorts_naturally() -> None:
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    plan = scan.execute(FIXTURES / "valid")

    assert [image.relative_path for image in plan.images] == [
        "pagina_1.png",
        "pagina_2.jpg",
        "pagina_10.webp",
    ]
    assert {image.media_type for image in plan.images} == {"image/png", "image/jpeg", "image/webp"}


def test_extension_and_decoded_content_must_match(tmp_path: Path) -> None:
    mismatch = tmp_path / "jpeg-disguised-as-png.png"
    mismatch.write_bytes((FIXTURES / "valid" / "pagina_2.jpg").read_bytes())
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageContentRejected):
        scan.execute(tmp_path)


def test_corrupt_image_aborts_the_full_source_scan() -> None:
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageContentRejected):
        scan.execute(FIXTURES / "invalid")


def test_dimensions_above_pixel_limit_are_rejected_before_full_decode(tmp_path: Path) -> None:
    over_limit = tmp_path / "wide.png"
    over_limit.write_bytes(_png_header(7072, 7072))
    scan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageLimitExceeded):
        scan.execute(tmp_path)


class OversizedSourceReader:
    def enumerate(self, _source_path: Path):
        from manga_to_kindle.application.images.import_source import ImageSourceManifest

        return ImageSourceManifest(
            ImageSourceKind.DIRECTORY,
            (ImageSourceFile("big.png", "big.png", 25 * 1024 * 1024 + 1),),
            0,
        )

    def read(self, _source_path: Path, _entry: ImageSourceFile, _limit: int) -> bytes:
        raise AssertionError("A leitura deve ser recusada pelos metadados antes do read.")


def _png_header(width: int, height: int) -> bytes:
    import struct
    import zlib

    payload = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"\x00" + b"\xff" * (width * 3)
    compressor = zlib.compressobj()
    compressed = b"".join(compressor.compress(rows) for _ in range(height))
    compressed += compressor.flush()
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", payload)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    import struct
    import zlib

    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def test_compressed_size_limit_is_checked_before_read(tmp_path: Path) -> None:
    scan = ScanImageSource(OversizedSourceReader(), PillowImageDecoder())

    with pytest.raises(ImageLimitExceeded):
        scan.execute(tmp_path)
