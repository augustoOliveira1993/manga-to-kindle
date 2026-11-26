from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from manga_to_kindle.domain.image_processing import ImageProcessingProfile
from manga_to_kindle.infrastructure.persistence.models import ChapterRecord, MangaRecord
from tests.image_support import make_image_stack


def test_empty_local_chapters_are_offered_as_import_targets(tmp_path: Path) -> None:
    database, image_root, _store, repository, _reader, _decoder, _importer = make_image_stack(
        tmp_path
    )
    manga_id = uuid4()
    chapter_id = uuid4()
    with database.unit_of_work() as session:
        session.add(
            MangaRecord(
                id=manga_id,
                title="Arquivo local",
                provider_id="local-import",
                simulated=False,
            )
        )
        session.add(
            ChapterRecord(
                id=chapter_id,
                manga_id=manga_id,
                position=0,
                title="Sem páginas",
            )
        )

    targets = repository.list_targets()

    assert len(targets) == 1
    assert targets[0].manga_title == "Arquivo local"
    assert targets[0].chapter_id == chapter_id
    assert ImageProcessingProfile().name == "Kindle Básico 10ª geração"
    assert image_root.is_relative_to(tmp_path)
    database.close()


def test_profile_can_be_overridden_per_import_without_mutating_default(tmp_path: Path) -> None:
    _database, _image_root, _store, _repository, _reader, _decoder, _importer = make_image_stack(
        tmp_path
    )
    default = ImageProcessingProfile()
    adjusted = ImageProcessingProfile(margin_left=12, margin_right=8)

    assert (default.margin_left, default.margin_right) == (0, 0)
    assert (adjusted.margin_left, adjusted.margin_right) == (12, 8)
