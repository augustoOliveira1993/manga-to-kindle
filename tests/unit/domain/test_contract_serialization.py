from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from manga_to_kindle.domain import (
    Chapter,
    DeviceProfile,
    DownloadJob,
    DownloadState,
    Export,
    ExportState,
    Manga,
    Page,
)


def _to_json_value(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_json_value(item) for item in value]
    return value


def test_all_six_domain_contracts_have_stable_json_values() -> None:
    manga_id = uuid4()
    chapter_id = uuid4()
    chapter = Chapter(manga_id=manga_id, id=chapter_id, position=0, number=Decimal("1.5"))
    profile = DeviceProfile(name="Personalizado", preferences={"reading_direction": "rtl"})
    values = (
        Manga(id=manga_id, title="Exemplo", chapters=(chapter,)),
        chapter,
        Page(chapter_id=chapter_id, position=0, original_path=Path("originais/001.webp")),
        DownloadJob(target_chapter_id=chapter_id, state=DownloadState.QUEUED, total=None),
        profile,
        Export(
            chapter_ids=(chapter_id,),
            device_profile=profile,
            destination=Path("C:/Users/teste/Exports/exemplo.epub"),
            state=ExportState.REQUESTED,
        ),
    )

    serialized = [json.loads(json.dumps(_to_json_value(value))) for value in values]

    assert len(serialized) == 6
    assert serialized[0]["id"] == str(manga_id)
    assert serialized[0]["chapters"][0]["number"] == "1.5"
    assert serialized[2]["original_path"] == "originais/001.webp"
    assert serialized[3]["state"] == "queued"
    assert serialized[4]["preferences"] == {"reading_direction": "rtl"}
    assert serialized[5]["chapter_ids"] == [str(chapter_id)]
    assert serialized[5]["state"] == "requested"
