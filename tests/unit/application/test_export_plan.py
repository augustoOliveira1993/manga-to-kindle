from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tests.export_support import fixture_sources, make_request

from manga_to_kindle.application.exports.errors import ExportPlanRejected
from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.domain.exports import ExportFormat, ExportGrouping, sanitize_filename_component


def test_plan_orders_chapters_and_pages_canonically_and_keeps_rtl_metadata() -> None:
    sources = fixture_sources()
    request = make_request(sources, chapter_indexes=(1, 0))

    plan = PlanExport().execute(sources, request)

    assert [package.chapter_ids for package in plan.packages] == [
        (sources[0].chapter.id,),
        (sources[1].chapter.id,),
    ]
    assert [len(package.pages) for package in plan.packages] == [2, 1]
    assert plan.direction.value == "rtl"
    assert plan.language == "pt-BR"
    assert plan.author is None
    assert all(package.identifier.startswith("urn:uuid:") for package in plan.packages)


def test_epub_requires_a_known_or_explicit_language() -> None:
    sources = fixture_sources(language=None)
    sources = tuple(
        replace(source, language=None)
        for source in sources
    )

    with pytest.raises(ExportPlanRejected, match="idioma"):
        PlanExport().execute(sources, make_request(sources))


def test_volume_grouping_rejects_unknown_volume_and_lists_actionable_error() -> None:
    sources = fixture_sources(volumes=("1", None))
    request = make_request(sources, grouping=ExportGrouping.VOLUME)

    with pytest.raises(ExportPlanRejected, match="volume conhecido"):
        PlanExport().execute(sources, request)


def test_volume_grouping_combines_pages_in_chapter_order() -> None:
    sources = fixture_sources()
    request = make_request(sources, grouping=ExportGrouping.VOLUME)

    plan = PlanExport().execute(sources, request)

    assert len(plan.packages) == 1
    package = plan.packages[0]
    assert package.title == "Coleção Sintética de Teste — Volume 1"
    assert package.chapter_ids == tuple(source.chapter.id for source in sources)
    assert [page.page_position for page in package.pages] == [0, 1, 0]


def test_plan_rejects_missing_chapters_processed_files_and_profile_mismatch(tmp_path: Path) -> None:
    sources = fixture_sources()
    missing_request = make_request(sources, chapter_indexes=(0,))
    with pytest.raises(ExportPlanRejected, match="não está mais disponível"):
        PlanExport().execute(sources[:0], missing_request)

    first = sources[0]
    missing_asset = replace(first.pages[0].processed[0], path=tmp_path / "missing.png")
    missing_page = replace(first.pages[0], processed=(missing_asset,))
    invalid_source = replace(first, pages=(missing_page, *first.pages[1:]))
    invalid_sources = (invalid_source, sources[1])
    with pytest.raises(ExportPlanRejected, match="não está disponível"):
        PlanExport().execute(invalid_sources, make_request(invalid_sources, chapter_indexes=(0,)))

    mismatch_profile = make_request(sources, chapter_indexes=(0,))
    from manga_to_kindle.domain.device_profile import DeviceProfile

    mismatch_profile = replace(
        mismatch_profile,
        profile=DeviceProfile("Outro", preferences={"width": 100, "height": 100}),
    )
    with pytest.raises(ExportPlanRejected, match="dimensões do perfil"):
        PlanExport().execute(sources, mismatch_profile)


def test_cbz_does_not_require_epub_language_and_name_is_sanitized() -> None:
    sources = fixture_sources(language=None)
    request = make_request(sources, format=ExportFormat.CBZ, language=None)

    plan = PlanExport().execute(sources, request)

    assert plan.language is None
    unsafe = sanitize_filename_component("../CON: volume? ")
    assert not unsafe.startswith(".")
    assert "/" not in unsafe and "\\" not in unsafe
