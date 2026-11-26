from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.export_support import fixture_sources, make_request

from manga_to_kindle.application.exports.errors import ExportPlanRejected
from manga_to_kindle.application.exports.partition import PartitionExport
from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.domain.exports import ExportGrouping


def test_volume_is_split_in_order_and_preserves_each_page(tmp_path: Path) -> None:
    sources = fixture_sources()
    request = make_request(
        sources,
        grouping=ExportGrouping.VOLUME,
        output_directory=tmp_path,
    )
    unsplit = PlanExport().execute(sources, request)
    page_bytes = sum(item.asset.path.stat().st_size for item in unsplit.packages[0].pages)
    limit = page_bytes + 28_000

    split = PartitionExport().execute(replace(unsplit, max_size_bytes=limit))

    assert len(split.packages) > 1
    assert [package.filename for package in split.packages] == [
        f"{Path(unsplit.packages[0].filename).stem}-parte-{index:03d}.epub"
        for index in range(1, len(split.packages) + 1)
    ]
    actual = [image.page_id for package in split.packages for image in package.pages]
    expected = [image.page_id for package in unsplit.packages for image in package.pages]
    assert actual == expected
    assert all(package.chapter_ids for package in split.packages)


def test_one_chapter_can_split_only_between_complete_pages(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(
        sources,
        make_request(sources, chapter_indexes=(0,), output_directory=tmp_path),
    )
    page_size = plan.packages[0].pages[0].asset.path.stat().st_size

    split = PartitionExport().execute(replace(plan, max_size_bytes=page_size + 24_100))

    assert len(split.packages) == 2
    assert [[image.page_position for image in package.pages] for package in split.packages] == [
        [0],
        [1],
    ]
    assert all(len(package.pages) == 1 for package in split.packages)


def test_rejects_limit_smaller_than_single_page(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(
        sources,
        make_request(sources, chapter_indexes=(0,), output_directory=tmp_path),
    )

    with pytest.raises(ExportPlanRejected, match="Uma página excede"):
        PartitionExport().execute(replace(plan, max_size_bytes=1024))


def test_preserves_chapter_boundaries_when_each_chapter_fits(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(
        sources,
        make_request(sources, grouping=ExportGrouping.VOLUME, output_directory=tmp_path),
    )

    split = PartitionExport().execute(replace(plan, max_size_bytes=30_000))

    assert len(split.packages) == 2
    assert [package.chapter_ids for package in split.packages] == [
        (sources[0].chapter.id,),
        (sources[1].chapter.id,),
    ]
