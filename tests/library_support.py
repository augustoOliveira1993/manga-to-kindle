from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

from manga_to_kindle.domain.catalog import CatalogSnapshot
from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.manga import Manga
from manga_to_kindle.infrastructure.persistence.catalog_repository import CatalogRepository
from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase

FIXTURES = Path(__file__).parent / "fixtures" / "library"


def seed_library(database: SQLiteDatabase) -> dict[str, UUID]:
    fixture = json.loads((FIXTURES / "catalog.json").read_text(encoding="utf-8"))
    result: dict[str, UUID] = {}
    for manga_data in cast(list[dict[str, object]], fixture["manga"]):
        manga_id = UUID(str(manga_data["id"]))
        chapters_data = cast(list[dict[str, object]], manga_data["chapters"])
        chapters = tuple(
            Chapter(
                manga_id=manga_id,
                id=UUID(str(chapter_data["id"])),
                position=position,
                title=str(chapter_data["title"]),
                number=Decimal(str(chapter_data["number"])),
                volume=(
                    Decimal(str(chapter_data["volume"]))
                    if chapter_data["volume"] is not None
                    else None
                ),
                available=True,
                source_order=position,
            )
            for position, chapter_data in enumerate(chapters_data)
        )
        title = str(manga_data["title"])
        source_id = f"library-demo:{manga_id}"
        snapshot = CatalogSnapshot(
            provider_id="library-demo",
            source_id=source_id,
            manga=Manga(
                id=manga_id,
                title=title,
                source_ref=source_id,
                author=(
                    str(manga_data["author"])
                    if manga_data["author"] is not None
                    else None
                ),
                chapters=chapters,
            ),
            updated_at=datetime.now(UTC),
            simulated=True,
        )
        CatalogRepository(database).replace(snapshot)
        result[title] = manga_id
        for chapter in chapters:
            result[f"{title}/{chapter.number}"] = chapter.id
    return result
