from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.images.import_pages import ImportImages
from manga_to_kindle.domain.image_processing import ImageImportTarget
from manga_to_kindle.infrastructure.images.image_store import ImageStore
from manga_to_kindle.infrastructure.images.pillow_decoder import PillowImageDecoder
from manga_to_kindle.infrastructure.images.source_reader import LocalImageSourceReader
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.image_import_repository import (
    ImageImportRepository,
)

FIXTURES = Path(__file__).parent / "fixtures" / "images"


def make_image_stack(tmp_path: Path):
    database = SQLiteDatabase(tmp_path / "profile" / "data" / "library.sqlite3")
    database.initialize()
    image_root = tmp_path / "profile" / "data" / "images"
    store = ImageStore(image_root)
    repository = ImageImportRepository(database, image_root)
    reader = LocalImageSourceReader()
    decoder = PillowImageDecoder()
    importer = ImportImages(reader, decoder, store, repository)
    return database, image_root, store, repository, reader, decoder, importer


def make_new_target(
    manga_title: str = "Demonstração local",
    chapter_title: str = "Capítulo importado",
) -> ImageImportTarget:
    return ImageImportTarget(
        manga_id=uuid4(),
        chapter_id=uuid4(),
        manga_title=manga_title,
        chapter_title=chapter_title,
        create_new=True,
    )
