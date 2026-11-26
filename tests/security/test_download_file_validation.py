from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from tests.download_support import VALID_PNG, NeverCancelled

from manga_to_kindle.application.downloads.errors import DownloadImageInvalid
from manga_to_kindle.infrastructure.downloads.page_store import PageStore


def test_page_store_accepts_png_and_preserves_exact_original_bytes(tmp_path: Path) -> None:
    store = PageStore(tmp_path / "managed")
    job_id, page_id, chapter_id = uuid4(), uuid4(), uuid4()
    original = VALID_PNG.read_bytes()

    artifact = store.stage_chunks(
        job_id=job_id,
        page_id=page_id,
        chapter_id=chapter_id,
        chunks=(original[:20], original[20:]),
        content_type="image/png; charset=binary",
        cancellation=NeverCancelled(),
    )

    assert artifact.image.byte_size == len(original)
    assert artifact.image.width == 1
    assert artifact.image.height == 1
    assert artifact.image.sha256
    assert artifact.temporary_path.read_bytes() == original


def test_page_store_rejects_mime_signature_corruption_and_oversized_pixels(
    tmp_path: Path,
) -> None:
    store = PageStore(tmp_path / "managed")
    original = VALID_PNG.read_bytes()

    with pytest.raises(DownloadImageInvalid):
        store.stage_chunks(
            job_id=uuid4(),
            page_id=uuid4(),
            chapter_id=uuid4(),
            chunks=(original,),
            content_type="image/jpeg",
            cancellation=NeverCancelled(),
        )

    with pytest.raises(DownloadImageInvalid):
        store.stage_chunks(
            job_id=uuid4(),
            page_id=uuid4(),
            chapter_id=uuid4(),
            chunks=(b"not-an-image",),
            content_type="image/png",
            cancellation=NeverCancelled(),
        )

    limited = PageStore(tmp_path / "small", max_compressed_bytes=64)
    with pytest.raises(DownloadImageInvalid):
        limited.stage_chunks(
            job_id=uuid4(),
            page_id=uuid4(),
            chapter_id=uuid4(),
            chunks=(b"x" * 65,),
            content_type="image/png",
            cancellation=NeverCancelled(),
        )

    oversized_path = tmp_path / "managed" / "oversized.png"
    oversized_path.parent.mkdir(parents=True, exist_ok=True)
    oversized_fixture = (
        Path(__file__).parents[1] / "fixtures" / "downloads" / "oversized_dimensions.png"
    )
    oversized_path.write_bytes(oversized_fixture.read_bytes())
    with pytest.raises(DownloadImageInvalid):
        store.validate_file(oversized_path, "image/png")


def test_page_store_accepts_exact_compressed_and_pixel_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = VALID_PNG.read_bytes()
    exact_size_store = PageStore(
        tmp_path / "exact-size",
        max_compressed_bytes=len(original),
    )
    artifact = exact_size_store.stage_chunks(
        job_id=uuid4(),
        page_id=uuid4(),
        chapter_id=uuid4(),
        chunks=(original,),
        content_type="image/png",
        cancellation=NeverCancelled(),
    )
    assert artifact.image.byte_size == len(original)

    class FakeDecodedImage:
        def __init__(self, width: int, height: int) -> None:
            self._width = width
            self._height = height

        def isNull(self) -> bool:
            return False

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height

    class FakeImageReader:
        def __init__(self, width: int, height: int) -> None:
            self._width = width
            self._height = height
            self.read_called = False

        def setDecideFormatFromContent(self, _enabled: bool) -> None:
            pass

        def size(self):
            from PySide6.QtCore import QSize

            return QSize(self._width, self._height)

        def read(self) -> FakeDecodedImage:
            self.read_called = True
            return FakeDecodedImage(self._width, self._height)

    reader = FakeImageReader(5000, 10_000)
    monkeypatch.setattr(
        "manga_to_kindle.infrastructure.downloads.page_store.QImageReader",
        lambda _path: reader,
    )
    boundary_file = tmp_path / "exact-size" / "boundary.png"
    boundary_file.write_bytes(original)
    validated = exact_size_store.validate_file(boundary_file, "image/png")
    assert validated.width * validated.height == 50_000_000
    assert reader.read_called

    over_limit_reader = FakeImageReader(5000, 10_001)
    monkeypatch.setattr(
        "manga_to_kindle.infrastructure.downloads.page_store.QImageReader",
        lambda _path: over_limit_reader,
    )
    with pytest.raises(DownloadImageInvalid):
        exact_size_store.validate_file(boundary_file, "image/png")
    assert not over_limit_reader.read_called
