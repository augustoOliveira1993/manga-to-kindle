"""Validação estrutural do CBZ nativo sem extrair arquivos no disco."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from manga_to_kindle.domain.exports import ExportPackagePlan


class CbzValidationError(ValueError):
    code = "CBZ_VALIDATION_FAILED"


class ValidateCbz:
    def execute(self, path: Path, package: ExportPackagePlan) -> int:
        return validate_cbz(path, package)


def validate_cbz(path: Path, package: ExportPackagePlan) -> int:
    if not path.is_absolute() or path.suffix.casefold() != ".cbz":
        raise CbzValidationError("O artefato precisa ser um caminho CBZ absoluto.")
    try:
        if path.is_symlink() or not path.resolve(strict=True).is_file():
            raise CbzValidationError("O CBZ não é um arquivo local regular.")
        with zipfile.ZipFile(path, "r") as archive:
            entries = archive.infolist()
            expected_names = [f"{index:05d}.png" for index in range(1, len(package.pages) + 1)]
            if [entry.filename for entry in entries] != expected_names:
                raise CbzValidationError("O CBZ omitiu páginas ou alterou a ordem das imagens.")
            if archive.testzip() is not None:
                raise CbzValidationError("Uma imagem do CBZ está corrompida.")
            for entry, image in zip(entries, package.pages, strict=True):
                if entry.file_size <= 0:
                    raise CbzValidationError("O CBZ contém uma página vazia.")
                digest = hashlib.sha256()
                with archive.open(entry, "r") as content:
                    while chunk := content.read(128 * 1024):
                        digest.update(chunk)
                if digest.hexdigest() != image.asset.sha256:
                    raise CbzValidationError("Uma imagem do CBZ difere da página processada.")
            return len(entries)
    except CbzValidationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError):
        raise CbzValidationError("O pacote CBZ está corrompido ou inacessível.") from None
