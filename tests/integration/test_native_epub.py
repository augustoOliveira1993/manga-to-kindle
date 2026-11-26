from __future__ import annotations

import hashlib
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.domain.exports import ExportGrouping
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.infrastructure.exports.epub_writer import (
    EpubSourceChanged,
    EpubWriteCancelled,
    NativeEpubWriter,
)
from tests.export_support import fixture_asset, fixture_sources, make_request

_OPF = "http://www.idpf.org/2007/opf"
_DC = "http://purl.org/dc/elements/1.1/"
_XHTML = "http://www.w3.org/1999/xhtml"


def test_native_epub_has_fixed_layout_metadata_cover_navigation_and_order(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(
        sources,
        make_request(sources, grouping=ExportGrouping.VOLUME),
    )
    package = plan.packages[0]
    destination = tmp_path / "volume.epub"

    result = NativeEpubWriter().write(plan, package, destination)

    assert result.path == destination
    assert result.size_bytes == destination.stat().st_size
    assert result.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    with zipfile.ZipFile(destination) as archive:
        entries = archive.infolist()
        assert entries[0].filename == "mimetype"
        assert entries[0].compress_type == zipfile.ZIP_STORED
        assert archive.read("mimetype") == b"application/epub+zip"
        package_doc = ET.fromstring(archive.read("EPUB/package.opf"))
        title = package_doc.findtext(f"{{{_OPF}}}metadata/{{{_DC}}}title")
        language = package_doc.findtext(f"{{{_OPF}}}metadata/{{{_DC}}}language")
        identifier = package_doc.findtext(f"{{{_OPF}}}metadata/{{{_DC}}}identifier")
        assert title == package.title
        assert language == "pt-BR"
        assert identifier is not None and identifier.startswith("urn:uuid:")
        assert package_doc.find(f".//{{{_DC}}}creator") is None
        meta = {
            item.attrib["property"]: item.text
            for item in package_doc.findall(f"{{{_OPF}}}metadata/{{{_OPF}}}meta")
        }
        assert meta["rendition:layout"] == "pre-paginated"
        assert meta["rendition:orientation"] == "portrait"
        assert meta["rendition:spread"] == "none"
        manifest = package_doc.find(f"{{{_OPF}}}manifest")
        assert manifest is not None
        cover = next(item for item in manifest if item.attrib.get("properties") == "cover-image")
        assert cover.attrib["href"] == "images/cover.svg"
        spine = package_doc.find(f"{{{_OPF}}}spine")
        assert spine is not None
        assert spine.attrib["page-progression-direction"] == "rtl"
        itemrefs = spine.findall(f"{{{_OPF}}}itemref")
        assert len(itemrefs) == 4  # capa e três páginas processadas
        nav = ET.fromstring(archive.read("EPUB/nav.xhtml"))
        nav_text = " ".join(nav.itertext())
        assert "Primeiro capítulo (1)" in nav_text
        assert "Segundo capítulo (2)" in nav_text
        assert len([name for name in archive.namelist() if name.endswith(".xhtml")]) == 5
        page_documents = [
            ET.fromstring(archive.read(name))
            for name in archive.namelist()
            if name.startswith("EPUB/text/") and name.endswith(".xhtml")
        ]
        assert all(
            document.find(f".//{{{_XHTML}}}meta[@name='viewport']").get("content")
            == "width=600,height=800"
            for document in page_documents
        )


def test_direction_is_written_as_ltr_and_source_cover_bytes_are_preserved(tmp_path: Path) -> None:
    sources = fixture_sources()
    cover_path = Path(__file__).parents[1] / "fixtures" / "exports" / "cover.png"
    source_cover = fixture_asset(cover_path)
    sources = tuple(replace(source, cover=source_cover) for source in sources)
    request = replace(
        make_request(sources, chapter_indexes=(0,)),
        direction=ReadingDirection.LEFT_TO_RIGHT,
    )
    plan = PlanExport().execute(sources, request)
    destination = tmp_path / "chapter.epub"

    NativeEpubWriter().write(plan, plan.packages[0], destination)

    with zipfile.ZipFile(destination) as archive:
        package_doc = ET.fromstring(archive.read("EPUB/package.opf"))
        spine = package_doc.find(f"{{{_OPF}}}spine")
        assert spine is not None and spine.attrib["page-progression-direction"] == "ltr"
        assert archive.read("EPUB/images/cover.png") == cover_path.read_bytes()


def test_metadata_is_text_and_never_becomes_markup_or_a_path(tmp_path: Path) -> None:
    sources = fixture_sources()
    sources = tuple(
        replace(
            source,
            manga_title='Coleção <teste> & “local”',
            chapter=replace(source.chapter, title="Capítulo <1> & conteúdo"),
        )
        for source in sources
    )
    request = make_request(sources, chapter_indexes=(0,))
    plan = PlanExport().execute(sources, request)
    package = plan.packages[0]
    destination = tmp_path / "safe.epub"

    NativeEpubWriter().write(plan, package, destination)

    with zipfile.ZipFile(destination) as archive:
        package_doc = ET.fromstring(archive.read("EPUB/package.opf"))
        title = package_doc.findtext(f"{{{_OPF}}}metadata/{{{_DC}}}title")
        assert title == package.title
        nav = ET.fromstring(archive.read("EPUB/nav.xhtml"))
        assert "Capítulo <1> & conteúdo (1)" in " ".join(nav.itertext())
        assert all(".." not in part for part in archive.namelist())
        for name in archive.namelist():
            if name.endswith(".xhtml"):
                document = ET.fromstring(archive.read(name))
                assert document.find(f".//{{{_XHTML}}}script") is None


def test_changed_page_hash_aborts_and_removes_partial_epub(tmp_path: Path) -> None:
    sources = fixture_sources()
    source = sources[0]
    asset = source.pages[0].processed[0]
    changed_path = tmp_path / "tampered.png"
    changed_path.write_bytes(b"tampered")
    changed_asset = replace(asset, path=changed_path)
    changed_page = replace(source.pages[0], processed=(changed_asset,))
    source = replace(source, pages=(changed_page, *source.pages[1:]))
    destination = tmp_path / "invalid.epub"
    request = make_request((source,), chapter_indexes=(0,))
    plan = PlanExport().execute((source,), request)

    with pytest.raises(EpubSourceChanged, match="checksum"):
        NativeEpubWriter().write(plan, plan.packages[0], destination)

    assert not destination.exists()


def test_cancellation_removes_only_the_partial_epub(tmp_path: Path) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(sources, make_request(sources, chapter_indexes=(0,)))
    destination = tmp_path / "cancelled.epub"

    class CancelImmediately:
        @property
        def cancelled(self) -> bool:
            return True

    with pytest.raises(EpubWriteCancelled):
        NativeEpubWriter().write(
            plan,
            plan.packages[0],
            destination,
            cancellation=CancelImmediately(),
        )

    assert not destination.exists()
