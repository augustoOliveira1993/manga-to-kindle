from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command

from manga_to_kindle.domain.image_processing import ImageProcessingProfile
from manga_to_kindle.infrastructure.persistence.export_repository import ExportRepository
from manga_to_kindle.infrastructure.persistence.models import (
    ChapterRecord,
    MangaRecord,
)
from tests.image_support import make_image_stack, make_new_target


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


def test_paperwhite_dimensions_and_profile_snapshot_flow_into_exportable_chapter(
    tmp_path: Path,
) -> None:
    database, _image_root, _store, repository, _reader, _decoder, importer = make_image_stack(
        tmp_path
    )
    target = make_new_target("Paperwhite local", "Página de teste")
    profile_id = uuid4()
    profile = ImageProcessingProfile(
        name="Kindle Paperwhite 10ª geração",
        width=1072,
        height=1448,
        profile_id=profile_id,
    )
    plan = importer.preview_source(Path(__file__).parent.parent / "fixtures" / "images" / "valid")

    importer.execute(
        plan,
        target,
        confirmed_authorization=True,
        profile=profile,
    )

    pages = repository.get_pages(target.chapter_id)
    processed = repository.get_processed_pages(pages[0].id)
    assert (processed[0].width, processed[0].height) == (1072, 1448)
    assert processed[0].profile_snapshot["profile_id"] == str(profile_id)
    assert len(ExportRepository(database).list_exportable_chapters()) == 1
    config = database._migration_config()
    with database.engine.connect() as connection:
        config.attributes["connection"] = connection
        with pytest.raises(RuntimeError, match="fora de 600 × 800"):
            command.downgrade(config, "0008_settings")
    assert database.current_revision() == "0011_mobi_export_artifacts"
    assert repository.get_processed_pages(pages[0].id)[0].width == 1072
    database.close()
