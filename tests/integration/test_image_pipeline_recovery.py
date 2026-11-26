from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.images.recovery import RecoverImageImports
from manga_to_kindle.domain.image_processing import (
    ImageProcessingProfile,
    ImageTransformOptions,
)
from tests.image_support import FIXTURES, make_image_stack, make_new_target


def test_interrupted_import_removes_its_staging_and_final_batch(tmp_path: Path) -> None:
    database, image_root, store, repository, _reader, decoder, importer = make_image_stack(tmp_path)
    plan = importer.preview_source(FIXTURES / "valid")
    target = make_new_target()
    job_id = uuid4()
    repository.start_job(job_id, plan, target)
    store.begin_batch(job_id)
    image = plan.images[0]
    source_bytes = (plan.source_path / image.relative_path).read_bytes()
    transformed = decoder.transform(
        source_bytes,
        ImageProcessingProfile(),
        ImageTransformOptions(),
        is_double_page=False,
    )
    store.stage_page(
        job_id,
        page_id=uuid4(),
        position=0,
        image=image,
        original_bytes=source_bytes,
        processed_bytes=transformed,
        duplicate_content=False,
    )
    store.promote_batch(job_id)

    count = RecoverImageImports(repository, store).execute()

    assert count == 1
    assert repository.get_job(job_id).state == "interrupted"
    assert not (image_root / ".staging" / str(job_id)).exists()
    assert not (image_root / "imports" / str(job_id)).exists()
    assert not repository.get_pages(target.chapter_id)
    database.close()
