from __future__ import annotations

import hashlib
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.domain.exports import ExportFormat
from manga_to_kindle.infrastructure.exports.cbz_writer import (
    CbzSourceChanged,
    NativeCbzWriter,
)
from tests.export_support import fixture_sources, make_request


def test_cbz_contains_processed_pages_in_order_and_preserves_identity(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(
        sources,
        make_request(
            sources,
            chapter_indexes=(0,),
            format=ExportFormat.CBZ,
            output_directory=tmp_path,
        ),
    )
    package = plan.packages[0]
    destination = tmp_path / "staged.cbz"

    result = NativeCbzWriter().write(plan, package, destination)

    assert result.page_count == len(package.pages) == 2
    assert result.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    with zipfile.ZipFile(destination) as archive:
        assert archive.namelist() == ["00001.png", "00002.png"]
        assert [archive.read(name) for name in archive.namelist()] == [
            image.asset.path.read_bytes() for image in package.pages
        ]


def test_cbz_rejects_changed_processed_image_and_removes_partial_file(tmp_path: Path) -> None:
    sources = fixture_sources()
    original = sources[0].pages[0].processed[0]
    changed = tmp_path / "changed.png"
    changed.write_bytes(b"changed")
    sources = (
        replace(
            sources[0],
            pages=(replace(sources[0].pages[0], processed=(replace(original, path=changed),)),),
        ),
    )
    plan = PlanExport().execute(
        sources,
        make_request(
            sources,
            chapter_indexes=(0,),
            format=ExportFormat.CBZ,
            output_directory=tmp_path,
        ),
    )
    destination = tmp_path / "changed.cbz"

    with pytest.raises(CbzSourceChanged, match="checksum"):
        NativeCbzWriter().write(plan, plan.packages[0], destination)

    assert not destination.exists()
