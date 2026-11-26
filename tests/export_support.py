from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.device_profile import DeviceProfile
from manga_to_kindle.domain.exports import (
    ExportAsset,
    ExportFormat,
    ExportGrouping,
    ExportPage,
    ExportRequest,
    ExportSourceChapter,
)

EXPORT_FIXTURES = Path(__file__).parent / "fixtures" / "exports"
_METADATA = json.loads((EXPORT_FIXTURES / "metadata.json").read_text(encoding="utf-8"))


def fixture_asset(path: Path, *, output_order: int = 0) -> ExportAsset:
    return ExportAsset(
        path=path.resolve(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        media_type="image/png",
        width=600,
        height=800,
        output_order=output_order,
    )


def fixture_sources(
    *,
    volumes: tuple[str | None, ...] = ("1", "1"),
    language: str | None = "pt-BR",
) -> tuple[ExportSourceChapter, ...]:
    manga_id = UUID(int=10)
    sources: list[ExportSourceChapter] = []
    for index, record in enumerate(_METADATA["chapters"]):
        directory = EXPORT_FIXTURES / record["directory"]
        pages = tuple(
            ExportPage(
                id=UUID(int=(index + 1) * 100 + position + 1),
                position=position,
                processed=(fixture_asset(path),),
            )
            for position, path in enumerate(sorted(directory.glob("*.png")))
        )
        chapter = Chapter(
            manga_id=manga_id,
            id=UUID(int=index + 1),
            position=index,
            title=record["title"],
            number=Decimal(record["number"]),
            source_order=index,
        )
        sources.append(
            ExportSourceChapter(
                chapter=chapter,
                manga_title=_METADATA["manga_title"],
                pages=pages,
                volume=volumes[index],
                author=_METADATA["author"],
                language=language,
            )
        )
    return tuple(sources)


def make_request(
    sources: tuple[ExportSourceChapter, ...],
    *,
    chapter_indexes: tuple[int, ...] = (0, 1),
    format: ExportFormat = ExportFormat.EPUB,
    grouping: ExportGrouping = ExportGrouping.CHAPTER,
    language: str | None = None,
    output_directory: Path | None = None,
) -> ExportRequest:
    return ExportRequest(
        chapter_ids=tuple(sources[index].chapter.id for index in chapter_indexes),
        output_directory=(output_directory or EXPORT_FIXTURES).resolve(),
        profile=DeviceProfile("Kindle Básico", preferences={"width": 600, "height": 800}),
        format=format,
        grouping=grouping,
        language=language,
    )
