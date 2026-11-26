from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.images.import_source import ScanImageSource
from manga_to_kindle.domain.image_processing import (
    ImageProcessingProfile,
    ImageTransformOptions,
)
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader
from tests.image_support import FIXTURES


def test_store_keeps_original_bytes_separate_from_processed_derivative(tmp_path: Path) -> None:
    source = FIXTURES / "valid" / "pagina_1.png"
    original = source.read_bytes()
    plan = ScanImageSource(LocalImageSourceReader(), PillowImageDecoder()).execute(source.parent)
    image = plan.images[0]
    processed = PillowImageDecoder().transform(
        original,
        ImageProcessingProfile(),
        ImageTransformOptions(),
        is_double_page=False,
    )
    store = ImageStore(tmp_path / "managed")
    batch_id = uuid4()
    store.begin_batch(batch_id)

    staged = store.stage_page(
        batch_id,
        page_id=uuid4(),
        position=0,
        image=image,
        original_bytes=original,
        processed_bytes=processed,
        duplicate_content=False,
    )
    store.promote_batch(batch_id)

    assert staged.final_original_path.read_bytes() == original
    assert hashlib.sha256(staged.final_original_path.read_bytes()).hexdigest() == image.sha256
    assert staged.final_original_path != staged.processed[0].final_path
    assert staged.processed[0].final_path.is_file()


def test_cleanup_removes_only_the_requested_managed_batch(tmp_path: Path) -> None:
    root = tmp_path / "managed"
    outside = tmp_path / "keep.txt"
    outside.write_text("preservado", encoding="utf-8")
    store = ImageStore(root)
    batch_id = uuid4()
    store.begin_batch(batch_id)
    store.cleanup(batch_id)

    assert outside.read_text(encoding="utf-8") == "preservado"
    assert not (root / ".staging" / str(batch_id)).exists()
    assert not (root / "imports" / str(batch_id)).exists()
