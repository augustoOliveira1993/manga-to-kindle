from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from PySide6.QtGui import QColor, QImage

from manga_to_kindle.application.downloads.errors import DownloadIdentityConflict
from manga_to_kindle.infrastructure.downloads.page_store import PageStore
from tests.download_support import VALID_PNG, NeverCancelled


def test_page_promotion_is_atomic_and_never_overwrites_another_content(
    tmp_path: Path,
) -> None:
    store = PageStore(tmp_path / "managed")
    job_id, page_id, chapter_id = uuid4(), uuid4(), uuid4()
    original = VALID_PNG.read_bytes()
    first = store.stage_chunks(
        job_id=job_id,
        page_id=page_id,
        chapter_id=chapter_id,
        chunks=(original,),
        content_type="image/png",
        cancellation=NeverCancelled(),
    )
    final_path = store.promote(first, job_id=job_id, page_id=page_id)
    assert final_path.read_bytes() == original
    assert not first.temporary_path.exists()

    different = QImage(1, 1, QImage.Format.Format_RGBA8888)
    different.fill(QColor("#18a36b"))
    alternate_file = tmp_path / "alternate.png"
    assert different.save(str(alternate_file), "PNG")
    second = store.stage_chunks(
        job_id=job_id,
        page_id=page_id,
        chapter_id=chapter_id,
        chunks=(alternate_file.read_bytes(),),
        content_type="image/png",
        cancellation=NeverCancelled(),
    )
    with pytest.raises(DownloadIdentityConflict):
        store.promote(second, job_id=job_id, page_id=page_id)

    assert final_path.read_bytes() == original
    assert not second.temporary_path.exists()
