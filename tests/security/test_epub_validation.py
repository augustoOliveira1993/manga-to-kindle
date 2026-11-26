from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from tests.export_support import fixture_sources, make_request

from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.infrastructure.exports.epub_validator import (
    EpubValidationError,
    ValidateEpub,
)
from manga_to_kindle.infrastructure.exports.epub_writer import NativeEpubWriter


def _write_epub(path: Path, *, replacements: dict[str, bytes] | None = None) -> None:
    sources = fixture_sources()
    plan = PlanExport().execute(sources, make_request(sources, chapter_indexes=(0,)))
    NativeEpubWriter().write(plan, plan.packages[0], path)
    if not replacements:
        return
    rewritten = path.with_suffix(".rewritten")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(rewritten, "w") as target:
        for item in source.infolist():
            content = replacements.get(item.filename, source.read(item.filename))
            target.writestr(item, content, compress_type=item.compress_type)
    rewritten.replace(path)


def test_native_epub_passes_internal_validation(tmp_path: Path) -> None:
    path = tmp_path / "valid.epub"
    _write_epub(path)

    report = ValidateEpub().execute(path)

    assert report.path == path
    assert report.entry_count > 5
    assert report.page_count == 2
    assert report.expanded_size_bytes > 0


@pytest.mark.parametrize(
    ("entry", "replacement"),
    [
        (
            "EPUB/nav.xhtml",
            b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" '
            b'lang="pt-BR"><body><nav xmlns:epub="http://www.idpf.org/2007/ops" '
            b'epub:type="toc"><ol><li><a href="https://example.invalid/book">cap</a>'
            b"</li></ol></nav></body></html>",
        ),
        (
            "EPUB/images/cover.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"><image '
            b'href="https://example.invalid/remote.png"/></svg>',
        ),
        (
            "EPUB/nav.xhtml",
            b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" '
            b'lang="pt-BR"><body><script>alert(1)</script><nav '
            b'xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><ol>'
            b'<li><a href="text/page-00001.xhtml">cap</a></li></ol></nav></body></html>',
        ),
        ("mimetype", b"text/plain"),
    ],
)
def test_rejects_external_script_and_invalid_mimetype(
    tmp_path: Path,
    entry: str,
    replacement: bytes,
) -> None:
    path = tmp_path / "invalid.epub"
    _write_epub(path, replacements={entry: replacement})

    with pytest.raises(EpubValidationError):
        ValidateEpub().execute(path)


def test_rejects_missing_manifest_resource(tmp_path: Path) -> None:
    path = tmp_path / "missing.epub"
    _write_epub(
        path,
        replacements={
            "EPUB/package.opf": (
                b'<?xml version="1.0" encoding="utf-8"?>'
                b'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
                b'unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
                b'<dc:identifier id="id">urn:uuid:test</dc:identifier><dc:title>Test</dc:title>'
                b'<dc:language>pt-BR</dc:language><meta property="rendition:layout">'
                b'pre-paginated</meta></metadata><manifest><item id="nav" href="missing.xhtml" '
                b'media-type="application/xhtml+xml" properties="nav"/></manifest>'
                b'<spine page-progression-direction="rtl"><itemref idref="nav"/></spine></package>'
            )
        },
    )

    with pytest.raises(EpubValidationError, match="recurso declarado"):
        ValidateEpub().execute(path)


def test_rejects_relative_traversal_in_container_path(tmp_path: Path) -> None:
    path = tmp_path / "traversal.epub"
    _write_epub(
        path,
        replacements={
            "META-INF/container.xml": (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" '
                b'version="1.0"><rootfiles><rootfile full-path="../package.opf" '
                b'media-type="application/oebps-package+xml"/></rootfiles></container>'
            )
        },
    )

    with pytest.raises(EpubValidationError):
        ValidateEpub().execute(path)
