"""Validação local dos recursos e referências de um EPUB antes da publicação."""

from __future__ import annotations

import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
_OPF = "http://www.idpf.org/2007/opf"
_DC = "http://purl.org/dc/elements/1.1/"
_XHTML = "http://www.w3.org/1999/xhtml"
_EPUB = "http://www.idpf.org/2007/ops"
_SVG = "http://www.w3.org/2000/svg"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_MAX_ENTRIES = 100_000
_MAX_XML_BYTES = 16 * 1024 * 1024
_MAX_EXPANDED_BYTES = 8 * 1024 * 1024 * 1024
_CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
_CSS_IMPORT = re.compile(r"@import\s+(['\"])(.*?)\1", re.IGNORECASE)


class EpubValidationError(ValueError):
    """O artefato não satisfaz os invariantes locais de publicação EPUB."""

    code = "EPUB_VALIDATION_FAILED"


@dataclass(frozen=True, slots=True)
class EpubValidationReport:
    path: Path
    entry_count: int
    page_count: int
    expanded_size_bytes: int


class ValidateEpub:
    """Verifica o fechamento local de recursos e o contrato EPUB 3 do writer."""

    def execute(self, path: Path) -> EpubValidationReport:
        if not path.is_absolute() or path.suffix.casefold() != ".epub":
            raise EpubValidationError("O artefato precisa ser um caminho EPUB absoluto.")
        try:
            if path.is_symlink() or not path.resolve(strict=True).is_file():
                raise EpubValidationError("O EPUB não é um arquivo local regular.")
            with zipfile.ZipFile(path, "r") as archive:
                return self._validate_archive(path, archive)
        except EpubValidationError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError, ET.ParseError):
            raise EpubValidationError("O pacote EPUB está corrompido ou inacessível.") from None

    def _validate_archive(
        self,
        path: Path,
        archive: zipfile.ZipFile,
    ) -> EpubValidationReport:
        entries = archive.infolist()
        if not entries or len(entries) > _MAX_ENTRIES:
            raise EpubValidationError("O pacote EPUB tem uma quantidade inválida de arquivos.")
        names = [entry.filename for entry in entries]
        if len(set(names)) != len(names):
            raise EpubValidationError("O pacote EPUB contém caminhos duplicados.")
        for name in names:
            _validate_zip_name(name)
        if any(entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16) for entry in entries):
            raise EpubValidationError("O pacote EPUB contém links ou entradas de diretório.")
        if names[0] != "mimetype" or entries[0].compress_type != zipfile.ZIP_STORED:
            raise EpubValidationError("O mimetype precisa ser o primeiro item sem compressão.")
        if entries[0].file_size != len(b"application/epub+zip"):
            raise EpubValidationError("O mimetype tem tamanho inválido.")
        if archive.read("mimetype") != b"application/epub+zip":
            raise EpubValidationError("O mimetype do pacote não identifica EPUB.")
        expanded = sum(entry.file_size for entry in entries)
        if expanded > _MAX_EXPANDED_BYTES:
            raise EpubValidationError("O pacote EPUB excede o limite local de leitura.")
        name_set = set(names)
        container = _parse_xml(_read_bounded(archive, "META-INF/container.xml"))
        rootfiles = container.findall(f"{{{_CONTAINER}}}rootfiles/{{{_CONTAINER}}}rootfile")
        if len(rootfiles) != 1:
            raise EpubValidationError("O contêiner precisa apontar para um único pacote OPF.")
        package_path = _resolve_href("", rootfiles[0].get("full-path", ""))
        if package_path not in name_set:
            raise EpubValidationError("O documento OPF não existe no pacote.")
        package = _parse_xml(_read_bounded(archive, package_path))
        if package.tag != f"{{{_OPF}}}package" or package.get("version") != "3.0":
            raise EpubValidationError("O documento OPF não declara EPUB 3.0.")
        metadata = package.find(f"{{{_OPF}}}metadata")
        manifest = package.find(f"{{{_OPF}}}manifest")
        spine = package.find(f"{{{_OPF}}}spine")
        if metadata is None or manifest is None or spine is None:
            raise EpubValidationError("Metadados, manifesto ou spine estão ausentes.")
        _require_text(metadata, f"{{{_DC}}}identifier")
        _require_text(metadata, f"{{{_DC}}}title")
        _require_text(metadata, f"{{{_DC}}}language")
        identifier = metadata.find(f"{{{_DC}}}identifier")
        unique_id = package.get("unique-identifier")
        if identifier is None or unique_id != identifier.get("id"):
            raise EpubValidationError("O identificador único do pacote é inconsistente.")
        properties = {
            item.get("property", ""): (item.text or "").strip()
            for item in metadata.findall(f"{{{_OPF}}}meta")
        }
        if properties.get("rendition:layout") != "pre-paginated":
            raise EpubValidationError("O EPUB não declara layout fixo.")

        items_by_id: dict[str, ET.Element] = {}
        resolved_by_id: dict[str, str] = {}
        nav_paths: list[str] = []
        cover_paths: list[str] = []
        for item in manifest.findall(f"{{{_OPF}}}item"):
            item_id = item.get("id", "")
            href = item.get("href", "")
            if not item_id or item_id in items_by_id or not href:
                raise EpubValidationError("O manifesto contém identidade ou caminho inválido.")
            resolved = _resolve_href(package_path, href)
            if resolved not in name_set:
                raise EpubValidationError("Um recurso declarado no manifesto está ausente.")
            items_by_id[item_id] = item
            resolved_by_id[item_id] = resolved
            if "nav" in item.get("properties", "").split():
                nav_paths.append(resolved)
            if "cover-image" in item.get("properties", "").split():
                cover_paths.append(resolved)
        if len(nav_paths) != 1 or len(cover_paths) != 1:
            raise EpubValidationError("O manifesto requer exatamente um sumário e uma capa.")
        cover_item = next(
            (
                item
                for item in items_by_id.values()
                if "cover-image" in item.get("properties", "").split()
            ),
            None,
        )
        if cover_item is None or not cover_item.get("media-type", "").startswith("image/"):
            raise EpubValidationError("A capa precisa ser uma imagem local do pacote.")
        has_remote_resources = any(
            "remote-resources" in item.get("properties", "").split()
            for item in items_by_id.values()
        )
        if has_remote_resources:
            raise EpubValidationError("O manifesto declara recursos externos.")

        spine_items = spine.findall(f"{{{_OPF}}}itemref")
        if not spine_items:
            raise EpubValidationError("A ordem de leitura do EPUB está vazia.")
        page_count = 0
        spine_paths: list[str] = []
        for itemref in spine_items:
            item_id = itemref.get("idref", "")
            spine_item = items_by_id.get(item_id)
            if spine_item is None or spine_item.get("media-type") != "application/xhtml+xml":
                raise EpubValidationError("O spine aponta para uma página inexistente.")
            spine_paths.append(resolved_by_id[item_id])
            page_count += 1
        if spine.get("page-progression-direction") not in {"ltr", "rtl"}:
            raise EpubValidationError("A direção de leitura do spine não é válida.")

        parsed_documents: dict[str, ET.Element] = {}
        for item_id, item in items_by_id.items():
            resource_path = resolved_by_id[item_id]
            media_type = item.get("media-type", "")
            if media_type == "application/xhtml+xml":
                document = _parse_xml(_read_bounded(archive, resource_path))
                if document.tag != f"{{{_XHTML}}}html":
                    raise EpubValidationError("Um documento XHTML não usa o namespace correto.")
                if not (document.get("lang") or document.get(_XML_LANG)):
                    raise EpubValidationError("Um documento XHTML está sem idioma.")
                if document.find(f".//{{{_XHTML}}}script") is not None:
                    raise EpubValidationError("Scripts não são permitidos no EPUB.")
                _validate_markup_references(document, resource_path, name_set)
                parsed_documents[resource_path] = document
            elif media_type == "text/css":
                css = _read_bounded(archive, resource_path).decode("utf-8")
                _validate_css_references(css, resource_path, name_set)
            elif media_type == "image/svg+xml":
                image = _parse_xml(_read_bounded(archive, resource_path))
                if image.tag != f"{{{_SVG}}}svg":
                    raise EpubValidationError("Uma imagem SVG não usa o namespace correto.")
                if image.find(f".//{{{_SVG}}}script") is not None:
                    raise EpubValidationError("Scripts SVG não são permitidos no EPUB.")
                _validate_markup_references(image, resource_path, name_set)
            elif not media_type.startswith("image/"):
                raise EpubValidationError("O manifesto contém um tipo de recurso não aceito.")

        nav_path = nav_paths[0]
        nav = parsed_documents.get(nav_path)
        if nav is None or nav.find(f".//{{{_XHTML}}}nav[@{{{_EPUB}}}type='toc']") is None:
            raise EpubValidationError("O EPUB não contém sumário navegável.")
        toc_links = nav.findall(f".//{{{_XHTML}}}nav[@{{{_EPUB}}}type='toc']//{{{_XHTML}}}a")
        if not toc_links:
            raise EpubValidationError("O sumário não possui entradas de capítulo.")
        for link in toc_links:
            _validate_link_target(link.get("href", ""), nav_path, name_set, parsed_documents)
        for spine_path in spine_paths:
            if spine_path not in parsed_documents:
                raise EpubValidationError("Uma página do spine não pôde ser validada.")
        return EpubValidationReport(path, len(entries), max(0, page_count - 1), expanded)


def _validate_zip_name(name: str) -> None:
    if not name or "\\" in name or "\x00" in name:
        raise EpubValidationError("O pacote contém um caminho ZIP inseguro.")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise EpubValidationError("O pacote contém um caminho ZIP fora da raiz.")
    if ":" in path.parts[0]:
        raise EpubValidationError("O pacote contém um caminho ZIP com unidade externa.")


def _resolve_href(base_file: str, href: str) -> str:
    if not href or "\\" in href or "\x00" in href:
        raise EpubValidationError("Uma referência interna contém caminho inválido.")
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.query:
        raise EpubValidationError("Referências externas ou consultas não são permitidas.")
    decoded = unquote(parsed.path)
    if not decoded or decoded.startswith("/"):
        raise EpubValidationError("Uma referência interna não aponta para um recurso local.")
    base = [] if not base_file else list(PurePosixPath(base_file).parent.parts)
    for part in PurePosixPath(decoded).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not base:
                raise EpubValidationError("Uma referência tenta sair da raiz do pacote.")
            base.pop()
        else:
            base.append(part)
    if not base:
        raise EpubValidationError("Uma referência não identifica um arquivo do pacote.")
    return "/".join(base)


def _read_bounded(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError:
        raise EpubValidationError("Um documento obrigatório está ausente do pacote.") from None
    if info.file_size > _MAX_XML_BYTES:
        raise EpubValidationError("Um documento XML/CSS excede o limite de validação local.")
    return archive.read(info)


def _parse_xml(content: bytes) -> ET.Element:
    try:
        return ET.fromstring(content)
    except ET.ParseError:
        raise EpubValidationError("Um documento XML do EPUB está malformado.") from None


def _require_text(parent: ET.Element, tag: str) -> None:
    node = parent.find(tag)
    if node is None or not (node.text or "").strip():
        raise EpubValidationError("O EPUB está sem um metadado obrigatório.")


def _validate_markup_references(
    root: ET.Element,
    document_path: str,
    names: set[str],
) -> None:
    active_elements = {"script", "iframe", "object", "embed", "form"}
    for node in root.iter():
        local_tag = node.tag.rsplit("}", maxsplit=1)[-1].casefold()
        if local_tag in active_elements:
            raise EpubValidationError("Elementos ativos não são permitidos no EPUB.")
        for attribute, value in node.attrib.items():
            local_name = attribute.rsplit("}", maxsplit=1)[-1].casefold()
            if local_name.startswith("on"):
                raise EpubValidationError("Atributos de script não são permitidos no EPUB.")
            if local_name == "base":
                raise EpubValidationError("Bases de URL não são permitidas no EPUB.")
            if local_name in {"href", "src", "poster", "action"}:
                _validate_link_target(value, document_path, names, None)
            elif local_name == "style":
                _validate_css_references(value, document_path, names)
            elif local_name == "http-equiv" and value.casefold() == "refresh":
                raise EpubValidationError("Redirecionamentos não são permitidos no EPUB.")


def _validate_css_references(css: str, document_path: str, names: set[str]) -> None:
    references = [match.group(2).strip() for match in _CSS_URL.finditer(css)]
    references.extend(match.group(2).strip() for match in _CSS_IMPORT.finditer(css))
    for reference in references:
        if reference.casefold().startswith("data:"):
            raise EpubValidationError("Recursos embutidos como data URI não são permitidos.")
        _validate_link_target(reference, document_path, names, None)


def _validate_link_target(
    href: str,
    source_path: str,
    names: set[str],
    documents: dict[str, ET.Element] | None,
) -> None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.query:
        raise EpubValidationError("O EPUB contém referência externa ou consulta.")
    if not parsed.path and parsed.fragment:
        target_path = source_path
    else:
        target_path = _resolve_href(source_path, parsed.path)
    if target_path not in names:
        raise EpubValidationError("O EPUB referencia um recurso interno ausente.")
    if parsed.fragment and documents is not None:
        target = documents.get(target_path)
        has_target = target is not None and any(
            node.get("id") == parsed.fragment for node in target.iter()
        )
        if not has_target:
            raise EpubValidationError("Um link do sumário aponta para uma âncora ausente.")
