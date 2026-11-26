"""Leitura segura de pastas e arquivos CBZ sem extração de nomes externos."""

from __future__ import annotations

import os
import stat
import unicodedata
from pathlib import Path, PurePosixPath

from manga_to_kindle.domain.image_processing import (
    MAX_SOURCE_ENTRIES,
    ImageLimitExceeded,
    ImageSourceFile,
    ImageSourceKind,
    ImageSourceManifest,
    ImageSourceRejected,
)
from manga_to_kindle.infrastructure.images.archive_reader import SafeArchiveReader
from manga_to_kindle.infrastructure.images.streaming import read_bounded


class LocalImageSourceReader:
    """Enumera a origem e lê apenas membros regulares sob os limites informados."""

    def __init__(self, archive_reader: SafeArchiveReader | None = None) -> None:
        self._archive_reader = archive_reader or SafeArchiveReader()

    def enumerate(self, source_path: Path) -> ImageSourceManifest:
        if source_path.suffix.casefold() == ".cbz":
            return self._archive_reader.enumerate(source_path)
        if not source_path.exists() or not source_path.is_dir():
            raise ImageSourceRejected("Selecione uma pasta ou um arquivo CBZ existente.")
        if _is_reparse_point(source_path):
            raise ImageSourceRejected("A pasta selecionada é um link e não pode ser importada.")
        return self._enumerate_directory(source_path)

    def read(self, source_path: Path, source_file: ImageSourceFile, limit: int) -> bytes:
        if limit < 0:
            raise ValueError("O limite de leitura não pode ser negativo.")
        if source_path.suffix.casefold() == ".cbz":
            return self._archive_reader.read(source_path, source_file, limit)
        return self._read_directory_file(source_path, source_file, limit)

    def _enumerate_directory(self, root: Path) -> ImageSourceManifest:
        files: list[ImageSourceFile] = []
        pending = [root]
        ignored = 0
        enumerated = 0
        seen_paths: set[str] = set()
        while pending:
            directory = pending.pop()
            try:
                children = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
            except OSError:
                raise ImageSourceRejected("Não foi possível ler a pasta selecionada.") from None
            for child in children:
                enumerated += 1
                if enumerated > MAX_SOURCE_ENTRIES:
                    raise ImageLimitExceeded("A origem contém mais de 10.000 itens.")
                path = Path(child.path)
                if _is_reparse_point(path):
                    ignored += 1
                    continue
                try:
                    if child.is_dir(follow_symlinks=False):
                        relative = path.relative_to(root).as_posix()
                        _register_directory_path(relative, seen_paths)
                        files.append(ImageSourceFile(relative, relative, 0, is_directory=True))
                        pending.append(path)
                    elif child.is_file(follow_symlinks=False):
                        relative = path.relative_to(root).as_posix()
                        _register_directory_path(relative, seen_paths)
                        file_size = child.stat(follow_symlinks=False).st_size
                        files.append(ImageSourceFile(relative, relative, file_size))
                    else:
                        ignored += 1
                except OSError:
                    raise ImageSourceRejected(
                        "Não foi possível examinar um item da pasta."
                    ) from None
        return ImageSourceManifest(ImageSourceKind.DIRECTORY, tuple(files), ignored)

    def _read_directory_file(self, root: Path, source_file: ImageSourceFile, limit: int) -> bytes:
        relative = PurePosixPath(source_file.locator)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ImageSourceRejected("Um caminho da pasta deixou de ser seguro.")
        path = root.joinpath(*relative.parts)
        try:
            root_resolved = root.resolve(strict=True)
            current = root
            for part in relative.parts:
                current = current / part
                if _is_reparse_point(current):
                    raise ImageSourceRejected("A pasta mudou durante a leitura.")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root_resolved) or not resolved.is_file():
                raise ImageSourceRejected("Um caminho da pasta deixou de ser seguro.")
            with resolved.open("rb") as stream:
                return read_bounded(stream, limit)
        except ImageSourceRejected:
            raise
        except OSError:
            raise ImageSourceRejected(
                "Uma imagem não pôde ser lida da pasta selecionada."
            ) from None

def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _windows_collision_key(value: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", part.rstrip(" .")).casefold()
        for part in value.split("/")
    )


def _register_directory_path(value: str, seen: set[str]) -> None:
    key = _windows_collision_key(value)
    if key in seen:
        raise ImageSourceRejected("A pasta contém nomes que colidem no Windows.")
    seen.add(key)
