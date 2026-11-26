"""Writer EPUB 3 fixed-layout usando apenas ZIP e XML da biblioteca padrão."""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import UUID
from xml.etree import ElementTree as ET

from manga_to_kindle.domain.exports import (
    ExportAsset,
    ExportFormat,
    ExportPackagePlan,
    ExportPlan,
    GeneratedPackage,
)

_OPF = "http://www.idpf.org/2007/opf"
_DC = "http://purl.org/dc/elements/1.1/"
_DCTERMS = "http://purl.org/dc/terms/"
_XHTML = "http://www.w3.org/1999/xhtml"
_EPUB = "http://www.idpf.org/2007/ops"
_SVG = "http://www.w3.org/2000/svg"
_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
_CHUNK_SIZE = 128 * 1024


class EpubWriteError(RuntimeError):
    code = "EPUB_WRITE_FAILED"


class EpubSourceChanged(EpubWriteError):
    code = "EPUB_SOURCE_CHANGED"


class EpubWriteCancelled(EpubWriteError):
    code = "EPUB_WRITE_CANCELLED"


class CancellationSignal(Protocol):
    @property
    def cancelled(self) -> bool: ...


type ProgressCallback = Callable[[int, int, str], None]


class NativeEpubWriter:
    def write(
        self,
        plan: ExportPlan,
        package: ExportPackagePlan,
        destination: Path,
        *,
        cancellation: CancellationSignal | None = None,
        report_progress: ProgressCallback | None = None,
    ) -> GeneratedPackage:
        if plan.format is not ExportFormat.EPUB or package not in plan.packages:
            raise EpubWriteError("O pacote não pertence a um plano EPUB válido.")
        if plan.language is None:
            raise EpubWriteError("O EPUB requer um idioma válido.")
        _validate_destination(destination)
        if destination.exists():
            raise EpubWriteError("O arquivo de estágio já existe.")
        if not package.pages:
            raise EpubWriteError("O pacote EPUB não contém páginas processadas.")
        width = package.pages[0].asset.width
        height = package.pages[0].asset.height

        cover_href = "images/cover.svg"
        if package.cover is not None:
            cover_href = "images/cover.png"
            cover_media_type = package.cover.media_type
        else:
            cover_media_type = "image/svg+xml"

        total_images = len(package.pages) + 1
        report = report_progress or (lambda _done, _total, _stage: None)
        created = False
        try:
            with destination.open("xb") as raw:
                created = True
                with zipfile.ZipFile(raw, mode="w", allowZip64=True) as archive:
                    self._write_mimetype(archive)
                    archive.writestr(
                        _zip_info("META-INF/container.xml"),
                        _container_document(),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
                    self._write_asset(
                        archive,
                        cover_href,
                        package.cover,
                        plan,
                        package,
                        cancellation,
                    )
                    done = 1
                    report(done, total_images, "Capa preparada")
                    for index, item in enumerate(package.pages, start=1):
                        _raise_if_cancelled(cancellation)
                        href = f"images/page-{index:05d}.png"
                        self._write_asset(
                            archive,
                            href,
                            item.asset,
                            plan,
                            package,
                            cancellation,
                        )
                        done += 1
                        report(done, total_images, f"Página {index} preparada")
                    self._write_text(
                        archive,
                        "styles/book.css",
                        _book_stylesheet(),
                    )
                    archive.writestr(
                        _zip_info("EPUB/nav.xhtml"),
                        _navigation_document(plan, package),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
                    archive.writestr(
                        _zip_info("EPUB/text/cover.xhtml"),
                        _cover_document(plan, package, cover_href, width, height),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
                    for index, item in enumerate(package.pages, start=1):
                        chapter_title = _chapter_title_for(package, item.chapter_id)
                        archive.writestr(
                            _zip_info(f"EPUB/text/page-{index:05d}.xhtml"),
                            _page_document(
                                language=plan.language,
                                page_number=index,
                                image_href=f"../images/page-{index:05d}.png",
                                title=chapter_title,
                                width=width,
                                height=height,
                            ),
                            compress_type=zipfile.ZIP_DEFLATED,
                        )
                    archive.writestr(
                        _zip_info("EPUB/package.opf"),
                        _package_document(plan, package, cover_media_type),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
            _raise_if_cancelled(cancellation)
            size_bytes = destination.stat().st_size
            if size_bytes <= 0:
                raise EpubWriteError("O EPUB gerado está vazio.")
            return GeneratedPackage(
                package_id=package.id,
                path=destination,
                sha256=_sha256_file(destination),
                size_bytes=size_bytes,
                page_count=len(package.pages),
            )
        except EpubWriteError:
            if created:
                destination.unlink(missing_ok=True)
            raise
        except OSError:
            if created:
                destination.unlink(missing_ok=True)
            raise EpubWriteError("Não foi possível escrever o arquivo EPUB local.") from None
        except Exception:
            if created:
                destination.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_mimetype(archive: zipfile.ZipFile) -> None:
        archive.writestr(
            _zip_info("mimetype", zipfile.ZIP_STORED),
            b"application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )

    @staticmethod
    def _write_text(
        archive: zipfile.ZipFile,
        relative_path: str,
        content: str,
    ) -> None:
        archive.writestr(
            _zip_info(f"EPUB/{relative_path}"),
            content.encode("utf-8"),
            compress_type=zipfile.ZIP_DEFLATED,
        )

    @staticmethod
    def _write_asset(
        archive: zipfile.ZipFile,
        relative_path: str,
        asset: ExportAsset | None,
        plan: ExportPlan,
        package: ExportPackagePlan,
        cancellation: CancellationSignal | None,
    ) -> None:
        if asset is None:
            archive.writestr(
                _zip_info(f"EPUB/{relative_path}"),
                _generated_cover_svg(package, plan.author).encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            return
        _validate_local_asset(asset)
        digest = hashlib.sha256()
        info = _zip_info(f"EPUB/{relative_path}", zipfile.ZIP_STORED)
        try:
            with asset.path.open("rb") as source:
                with archive.open(info, mode="w", force_zip64=True) as target:
                    while True:
                        _raise_if_cancelled(cancellation)
                        chunk = source.read(_CHUNK_SIZE)
                        if not chunk:
                            break
                        digest.update(chunk)
                        target.write(chunk)
        except EpubWriteError:
            raise
        except OSError:
            raise EpubSourceChanged("Uma imagem local não pôde ser lida.") from None
        if digest.hexdigest() != asset.sha256:
            raise EpubSourceChanged("O checksum de uma imagem mudou durante a exportação.")


def _validate_destination(destination: Path) -> None:
    if not destination.is_absolute() or destination.suffix.casefold() != ".epub":
        raise EpubWriteError("O destino do EPUB precisa ser um caminho .epub absoluto.")
    try:
        parent = destination.parent.resolve(strict=True)
        if destination.parent.is_symlink() or not parent.is_dir():
            raise OSError("A pasta de estágio não é regular.")
    except OSError:
        raise EpubWriteError("A pasta de estágio do EPUB não está disponível.") from None


def _validate_local_asset(asset: ExportAsset) -> None:
    try:
        resolved = asset.path.resolve(strict=True)
        if asset.path.is_symlink() or not resolved.is_file():
            raise OSError("A página processada não é arquivo regular.")
    except OSError:
        raise EpubSourceChanged("Uma página processada deixou de estar disponível.") from None


def _raise_if_cancelled(cancellation: CancellationSignal | None) -> None:
    if cancellation is not None and cancellation.cancelled:
        raise EpubWriteCancelled("A exportação EPUB foi cancelada.")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info(path: str, compression: int = zipfile.ZIP_DEFLATED) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = compression
    info.external_attr = 0o100600 << 16
    return info


def _container_document() -> bytes:
    root = ET.Element(f"{{{_CONTAINER}}}container", {"version": "1.0"})
    files = ET.SubElement(root, f"{{{_CONTAINER}}}rootfiles")
    ET.SubElement(
        files,
        f"{{{_CONTAINER}}}rootfile",
        {
            "full-path": "EPUB/package.opf",
            "media-type": "application/oebps-package+xml",
        },
    )
    return _xml_bytes(root, namespaces={"": _CONTAINER})


def _package_document(
    plan: ExportPlan,
    package: ExportPackagePlan,
    cover_media_type: str,
) -> bytes:
    ET.register_namespace("", _OPF)
    ET.register_namespace("dc", _DC)
    ET.register_namespace("dcterms", _DCTERMS)
    root = ET.Element(
        f"{{{_OPF}}}package",
        {
            "version": "3.0",
            "unique-identifier": "pub-id",
            "xml:lang": plan.language or "en",
        },
    )
    metadata = ET.SubElement(root, f"{{{_OPF}}}metadata")
    ET.SubElement(metadata, f"{{{_DC}}}identifier", {"id": "pub-id"}).text = package.identifier
    ET.SubElement(metadata, f"{{{_DC}}}title").text = package.title
    ET.SubElement(metadata, f"{{{_DC}}}language").text = plan.language or ""
    if plan.author is not None:
        ET.SubElement(metadata, f"{{{_DC}}}creator").text = plan.author
    modified = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _meta(metadata, "dcterms:modified", modified)
    _meta(metadata, "rendition:layout", "pre-paginated")
    _meta(metadata, "rendition:orientation", "portrait")
    _meta(metadata, "rendition:spread", "none")

    manifest = ET.SubElement(root, f"{{{_OPF}}}manifest")
    ET.SubElement(
        manifest,
        f"{{{_OPF}}}item",
        {
            "id": "nav",
            "href": "nav.xhtml",
            "media-type": "application/xhtml+xml",
            "properties": "nav",
        },
    )
    ET.SubElement(
        manifest,
        f"{{{_OPF}}}item",
        {
            "id": "cover-image",
            "href": f"images/cover.{_image_extension(cover_media_type)}",
            "media-type": cover_media_type,
            "properties": "cover-image",
        },
    )
    ET.SubElement(
        manifest,
        f"{{{_OPF}}}item",
        {
            "id": "cover-page",
            "href": "text/cover.xhtml",
            "media-type": "application/xhtml+xml",
        },
    )
    for index in range(1, len(package.pages) + 1):
        ET.SubElement(
            manifest,
            f"{{{_OPF}}}item",
            {
                "id": f"page-{index:05d}",
                "href": f"text/page-{index:05d}.xhtml",
                "media-type": "application/xhtml+xml",
            },
        )
        ET.SubElement(
            manifest,
            f"{{{_OPF}}}item",
            {
                "id": f"image-{index:05d}",
                "href": f"images/page-{index:05d}.png",
                "media-type": "image/png",
            },
        )
    ET.SubElement(
        manifest,
        f"{{{_OPF}}}item",
        {
            "id": "book-styles",
            "href": "styles/book.css",
            "media-type": "text/css",
        },
    )
    spine = ET.SubElement(
        root,
        f"{{{_OPF}}}spine",
        {"page-progression-direction": plan.direction.value},
    )
    ET.SubElement(spine, f"{{{_OPF}}}itemref", {"idref": "cover-page"})
    for index in range(1, len(package.pages) + 1):
        ET.SubElement(spine, f"{{{_OPF}}}itemref", {"idref": f"page-{index:05d}"})
    return _xml_bytes(root)


def _meta(parent: ET.Element, property_name: str, value: str) -> None:
    ET.SubElement(parent, f"{{{_OPF}}}meta", {"property": property_name}).text = value


def _navigation_document(plan: ExportPlan, package: ExportPackagePlan) -> bytes:
    ET.register_namespace("", _XHTML)
    ET.register_namespace("epub", _EPUB)
    root = ET.Element(
        f"{{{_XHTML}}}html",
        {
            "lang": plan.language or "en",
            "{http://www.w3.org/XML/1998/namespace}lang": plan.language or "en",
        },
    )
    head = ET.SubElement(root, f"{{{_XHTML}}}head")
    ET.SubElement(head, f"{{{_XHTML}}}title").text = package.title
    body = ET.SubElement(root, f"{{{_XHTML}}}body")
    nav = ET.SubElement(body, f"{{{_XHTML}}}nav", {f"{{{_EPUB}}}type": "toc", "id": "toc"})
    ET.SubElement(nav, f"{{{_XHTML}}}h1").text = "Sumário"
    listing = ET.SubElement(nav, f"{{{_XHTML}}}ol")
    first_pages: dict[UUID, str] = {}
    for index, item in enumerate(package.pages, start=1):
        first_pages.setdefault(item.chapter_id, f"text/page-{index:05d}.xhtml")
    for chapter_id, title in package.chapter_titles:
        nav_item = ET.SubElement(listing, f"{{{_XHTML}}}li")
        anchor = ET.SubElement(
            nav_item,
            f"{{{_XHTML}}}a",
            {"href": first_pages[chapter_id]},
        )
        anchor.text = title
    return _xml_bytes(root)


def _cover_document(
    plan: ExportPlan,
    package: ExportPackagePlan,
    cover_href: str,
    width: int,
    height: int,
) -> bytes:
    root, head, body = _xhtml_shell(plan.language or "en", package.title)
    head.append(_viewport_meta(width, height))
    head.append(_stylesheet_link("../styles/book.css"))
    wrapper = ET.SubElement(body, f"{{{_XHTML}}}div", {"class": "cover"})
    image = ET.SubElement(
        wrapper,
        f"{{{_XHTML}}}img",
        {"src": f"../{cover_href}", "alt": "Capa gerada" if package.cover is None else "Capa"},
    )
    image.tail = None
    return _xml_bytes(root)


def _page_document(
    *,
    language: str,
    page_number: int,
    image_href: str,
    title: str,
    width: int,
    height: int,
) -> bytes:
    root, head, body = _xhtml_shell(language, f"{title} — página {page_number}")
    head.append(_viewport_meta(width, height))
    head.append(_stylesheet_link("../styles/book.css"))
    image = ET.SubElement(
        body,
        f"{{{_XHTML}}}img",
        {"src": image_href, "alt": f"Página {page_number}"},
    )
    image.tail = None
    return _xml_bytes(root)


def _xhtml_shell(language: str, title: str) -> tuple[ET.Element, ET.Element, ET.Element]:
    ET.register_namespace("", _XHTML)
    root = ET.Element(
        f"{{{_XHTML}}}html",
        {
            "lang": language,
            "{http://www.w3.org/XML/1998/namespace}lang": language,
        },
    )
    head = ET.SubElement(root, f"{{{_XHTML}}}head")
    ET.SubElement(head, f"{{{_XHTML}}}title").text = title
    body = ET.SubElement(root, f"{{{_XHTML}}}body")
    return root, head, body


def _stylesheet_link(href: str) -> ET.Element:
    return ET.Element(
        f"{{{_XHTML}}}link",
        {"rel": "stylesheet", "type": "text/css", "href": href},
    )


def _viewport_meta(width: int, height: int) -> ET.Element:
    return ET.Element(
        f"{{{_XHTML}}}meta",
        {"name": "viewport", "content": f"width={width},height={height}"},
    )


def _book_stylesheet() -> str:
    return (
        "html, body { width: 100%; height: 100%; margin: 0; padding: 0; }\n"
        "body { overflow: hidden; }\n"
        "body > img, .cover > img { display: block; width: 100%; height: 100%; }\n"
        ".cover { width: 100%; height: 100%; }\n"
    )


def _generated_cover_svg(package: ExportPackagePlan, author: str | None) -> str:
    ET.register_namespace("", _SVG)
    width = package.pages[0].asset.width
    height = package.pages[0].asset.height
    root = ET.Element(
        f"{{{_SVG}}}svg",
        {
            "viewBox": f"0 0 {width} {height}",
            "width": str(width),
            "height": str(height),
        },
    )
    ET.SubElement(
        root,
        f"{{{_SVG}}}rect",
        {"width": str(width), "height": str(height), "fill": "#f4f1de"},
    )
    ET.SubElement(
        root,
        f"{{{_SVG}}}rect",
        {
            "x": str(width * 8 // 100),
            "y": str(height * 6 // 100),
            "width": str(width * 84 // 100),
            "height": str(height * 88 // 100),
            "fill": "none",
            "stroke": "#30343b",
            "stroke-width": "4",
        },
    )
    title_lines = _wrap_title(package.title)
    longest_line = max(map(len, title_lines))
    font_size = max(14, min(30, width * 60 // 100 // longest_line))
    line_height = font_size + max(12, height // 45)
    y = height // 2 - (len(title_lines) * line_height) // 2
    for line in title_lines:
        node = ET.SubElement(
            root,
            f"{{{_SVG}}}text",
            {
                "x": str(width // 2),
                "y": str(y),
                "text-anchor": "middle",
                "font-family": "sans-serif",
                "font-size": str(font_size),
                "fill": "#30343b",
            },
        )
        node.text = line
        y += line_height
    if author is not None:
        author_node = ET.SubElement(
            root,
            f"{{{_SVG}}}text",
            {
                "x": str(width // 2),
                "y": str(height * 67 // 100),
                "text-anchor": "middle",
                "font-family": "sans-serif",
                "font-size": "22",
                "fill": "#555555",
            },
        )
        author_node.text = author
    return _xml_text(root)


def _wrap_title(value: str, maximum: int = 38) -> tuple[str, ...]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > maximum:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return tuple(lines) or ("Exportação local",)


def _chapter_title_for(package: ExportPackagePlan, chapter_id: UUID) -> str:
    return next(title for identity, title in package.chapter_titles if identity == chapter_id)


def _image_extension(media_type: str) -> str:
    return "svg" if media_type == "image/svg+xml" else "png"


def _xml_bytes(root: ET.Element, *, namespaces: dict[str, str] | None = None) -> bytes:
    if namespaces:
        for prefix, uri in namespaces.items():
            ET.register_namespace(prefix, uri)
    return cast(
        bytes,
        ET.tostring(root, encoding="utf-8", xml_declaration=True, short_empty_elements=True),
    )


def _xml_text(root: ET.Element) -> str:
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)
