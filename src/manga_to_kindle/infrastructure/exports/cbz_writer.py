"""Writer local de CBZ com imagens processadas na sequência do plano."""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Callable
from pathlib import Path

from manga_to_kindle.domain.exports import (
    ExportFormat,
    ExportPackagePlan,
    ExportPlan,
    GeneratedPackage,
)
from manga_to_kindle.infrastructure.exports.epub_writer import (
    _CHUNK_SIZE,
    CancellationSignal,
    EpubWriteCancelled,
    _raise_if_cancelled,
    _validate_local_asset,
    _zip_info,
)


class CbzWriteError(RuntimeError):
    code = "CBZ_WRITE_FAILED"


class CbzSourceChanged(CbzWriteError):
    code = "CBZ_SOURCE_CHANGED"


type ProgressCallback = Callable[[int, int, str], None]


class NativeCbzWriter:
    def write(
        self,
        plan: ExportPlan,
        package: ExportPackagePlan,
        destination: Path,
        *,
        cancellation: CancellationSignal | None = None,
        report_progress: ProgressCallback | None = None,
    ) -> GeneratedPackage:
        if plan.format is not ExportFormat.CBZ or package not in plan.packages:
            raise CbzWriteError("O pacote não pertence a um plano CBZ válido.")
        _validate_cbz_destination(destination)
        if destination.exists():
            raise CbzWriteError("O destino temporário CBZ é inválido ou já existe.")
        created = False
        try:
            with destination.open("xb") as raw:
                created = True
                with zipfile.ZipFile(raw, mode="w", allowZip64=True) as archive:
                    for index, image in enumerate(package.pages, start=1):
                        _raise_if_cancelled(cancellation)
                        _validate_local_asset(image.asset)
                        digest = hashlib.sha256()
                        with image.asset.path.open("rb") as source:
                            with archive.open(
                                _zip_info(f"{index:05d}.png", zipfile.ZIP_STORED),
                                mode="w",
                                force_zip64=True,
                            ) as target:
                                while chunk := source.read(_CHUNK_SIZE):
                                    _raise_if_cancelled(cancellation)
                                    digest.update(chunk)
                                    target.write(chunk)
                        if digest.hexdigest() != image.asset.sha256:
                            raise CbzSourceChanged(
                                "O checksum de uma página mudou durante a exportação CBZ."
                            )
                        _report(report_progress, index, len(package.pages), index)
            _raise_if_cancelled(cancellation)
            size = destination.stat().st_size
            if not size:
                raise CbzWriteError("O CBZ gerado está vazio.")
            return GeneratedPackage(
                package.id,
                destination,
                _sha256_file(destination),
                size,
                len(package.pages),
            )
        except (CbzWriteError, EpubWriteCancelled):
            if created:
                destination.unlink(missing_ok=True)
            raise
        except OSError:
            if created:
                destination.unlink(missing_ok=True)
            raise CbzWriteError("Não foi possível escrever o arquivo CBZ local.") from None
        except Exception:
            if created:
                destination.unlink(missing_ok=True)
            raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _report(
    callback: ProgressCallback | None,
    completed: int,
    total: int,
    index: int,
) -> None:
    if callback is not None:
        callback(completed, total, f"Página {index} preparada")


def _validate_cbz_destination(destination: Path) -> None:
    if not destination.is_absolute() or destination.suffix.casefold() != ".cbz":
        raise CbzWriteError("O destino CBZ precisa ser um caminho .cbz absoluto.")
    try:
        if destination.parent.is_symlink() or not destination.parent.resolve(strict=True).is_dir():
            raise OSError("A pasta de estágio não é regular.")
    except OSError:
        raise CbzWriteError("A pasta de estágio do CBZ não está disponível.") from None
