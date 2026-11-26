"""Leitor CBZ que valida todos os nomes e nunca extrai caminhos do arquivo."""

from __future__ import annotations

import re
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

from manga_to_kindle.domain.image_processing import (
    MAX_SOURCE_ENTRIES,
    ImageLimitExceeded,
    ImageSourceFile,
    ImageSourceKind,
    ImageSourceManifest,
    ImageSourceRejected,
)
from manga_to_kindle.infrastructure.images.streaming import read_bounded


class SafeArchiveReader:
    def enumerate(self, archive_path: Path) -> ImageSourceManifest:
        if not archive_path.is_file() or _is_reparse_point(archive_path):
            raise ImageSourceRejected("Selecione um arquivo CBZ local regular.")
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                entries = archive.infolist()
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
            raise ImageSourceRejected("O arquivo CBZ não é um arquivo compactado válido.") from None
        if len(entries) > MAX_SOURCE_ENTRIES:
            raise ImageLimitExceeded("O CBZ contém mais de 10.000 entradas.")
        files: list[ImageSourceFile] = []
        seen: set[str] = set()
        ignored = 0
        for info in entries:
            relative = _validate_zip_name(info.filename)
            normalized = _windows_collision_key(relative)
            if normalized in seen:
                raise ImageSourceRejected("O CBZ contém nomes repetidos no Windows.")
            seen.add(normalized)
            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ImageSourceRejected("O CBZ contém uma entrada especial ou link.")
            if info.flag_bits & 0x1:
                raise ImageSourceRejected("CBZ protegido por senha não pode ser importado.")
            files.append(
                ImageSourceFile(
                    relative_path=relative,
                    locator=info.filename,
                    declared_size=info.file_size,
                    is_directory=info.is_dir() or file_type == stat.S_IFDIR,
                )
            )
            if info.is_dir():
                ignored += 1
        return ImageSourceManifest(ImageSourceKind.CBZ, tuple(files), ignored)

    def read(self, archive_path: Path, source_file: ImageSourceFile, limit: int) -> bytes:
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                info = archive.getinfo(source_file.locator)
                _validate_zip_name(info.filename)
                if info.flag_bits & 0x1 or info.is_dir():
                    raise ImageSourceRejected("O conteúdo do CBZ mudou depois da prévia.")
                with archive.open(info, "r") as stream:
                    return read_bounded(stream, limit)
        except ImageSourceRejected:
            raise
        except (OSError, KeyError, zipfile.BadZipFile, RuntimeError, zipfile.LargeZipFile):
            raise ImageSourceRejected("Uma imagem não pôde ser lida do CBZ selecionado.") from None


def _validate_zip_name(value: str) -> str:
    if not value or "\x00" in value or "\\" in value:
        raise ImageSourceRejected("O CBZ contém um caminho ambíguo ou inválido.")
    if value.startswith("/") or value.startswith("//") or re.match(r"^[A-Za-z]:", value):
        raise ImageSourceRejected("O CBZ contém um caminho absoluto.")
    raw_parts = value.rstrip("/").split("/")
    if not raw_parts or any(part in {"", ".", ".."} for part in raw_parts):
        raise ImageSourceRejected("O CBZ contém um caminho fora da pasta selecionada.")
    if any(":" in part for part in raw_parts):
        raise ImageSourceRejected("O CBZ contém um caminho de unidade inválido.")
    normalized_parts = [part.rstrip(" .") for part in raw_parts]
    if any(not part for part in normalized_parts):
        raise ImageSourceRejected("O CBZ contém um nome de arquivo inválido no Windows.")
    return PurePosixPath(*raw_parts).as_posix()


def _windows_collision_key(value: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", part.rstrip(" .")).casefold()
        for part in value.split("/")
    )


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & reparse_flag)
