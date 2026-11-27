"""Adaptador opcional para a CLI KCC 13.0.4 verificada durante a F007."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from manga_to_kindle.application.exports.ports import CancellationPort
from manga_to_kindle.domain.exports import (
    ExportFormat,
    ExportPackagePlan,
    ExportPlan,
    GeneratedPackage,
)
from manga_to_kindle.domain.image_processing import ReadingDirection

_VERIFIED_VERSION = "13.0.4"
_HELP_TIMEOUT_SECONDS = 15
_CONVERSION_TIMEOUT_SECONDS = 15 * 60
_POLL_INTERVAL_SECONDS = 0.1
_COPY_CHUNK_BYTES = 1024 * 1024
_MOBI_HEADER_OFFSET = 60
_MOBI_SIGNATURE = b"BOOKMOBI"
_REQUIRED_OPTIONS = frozenset(
    {
        "--profile",
        "--manga-style",
        "--cropping",
        "--output",
        "--title",
        "--filename",
        "--format",
        "--author",
        "--language",
    }
)


class KccAdapterError(RuntimeError):
    code = "KCC_ADAPTER_FAILED"


class KccExecutableUnavailable(KccAdapterError):
    code = "KCC_EXECUTABLE_UNAVAILABLE"


class KccVersionUnsupported(KccAdapterError):
    code = "KCC_VERSION_UNSUPPORTED"


class KccProfileUnsupported(KccAdapterError):
    code = "KCC_PROFILE_UNSUPPORTED"


class KccLanguageRequired(KccAdapterError):
    code = "KCC_LANGUAGE_REQUIRED"


class KccSizeLimitUnsupported(KccAdapterError):
    code = "KCC_SIZE_LIMIT_UNSUPPORTED"


class KccTimedOut(KccAdapterError):
    code = "KCC_TIMEOUT"


class KccConversionFailed(KccAdapterError):
    code = "KCC_CONVERSION_FAILED"


class KccOutputInvalid(KccAdapterError):
    code = "KCC_OUTPUT_INVALID"


class KccWriteCancelled(KccAdapterError):
    code = "EXPORT_CANCELLED"


class KccSourceChanged(KccAdapterError):
    code = "KCC_SOURCE_CHANGED"


class KccCliWriter:
    """Executa somente a versão e as opções KCC verificadas, sem shell ou rede do app."""

    def __init__(
        self,
        executable_path: Path,
        *,
        timeout_seconds: float = _CONVERSION_TIMEOUT_SECONDS,
        popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._executable_path = executable_path
        self._timeout_seconds = timeout_seconds
        self._popen = popen
        self._run = run
        self._monotonic = monotonic
        self._sleep = sleep
        self._verified_executable: Path | None = None

    def write(
        self,
        plan: ExportPlan,
        package: ExportPackagePlan,
        destination: Path,
        *,
        cancellation: CancellationPort | None = None,
        report_progress: Callable[[int, int, str], None] | None = None,
    ) -> GeneratedPackage:
        if plan.format is not ExportFormat.MOBI or package not in plan.packages:
            raise KccAdapterError("O pacote não pertence a um plano MOBI válido.")
        if not destination.is_absolute() or destination.suffix.casefold() != ".mobi":
            raise KccAdapterError("O destino MOBI local é inválido.")
        if destination.exists():
            raise KccAdapterError("O destino MOBI temporário já existe.")
        if not package.pages:
            raise KccAdapterError("O pacote MOBI não contém páginas processadas.")
        if plan.language is None:
            raise KccLanguageRequired("Informe o idioma dos metadados antes de criar MOBI.")
        if plan.max_size_bytes is not None:
            raise KccSizeLimitUnsupported(
                "A divisão por tamanho da CLI KCC não foi verificada para saída MOBI."
            )
        _raise_if_cancelled(cancellation)
        executable = self._verify_executable(destination.parent)
        profile = _profile_for_dimensions(
            plan.profile.preferences.get("width"),
            plan.profile.preferences.get("height"),
        )

        workspace = destination.parent / "kcc-work"
        input_directory = workspace / "input"
        output_directory = workspace / "output"
        try:
            input_directory.mkdir(parents=True, exist_ok=False)
            output_directory.mkdir(parents=True, exist_ok=False)
            _report(report_progress, 0, len(package.pages) + 1, "Preparando páginas para KCC")
            for index, image in enumerate(package.pages, start=1):
                _raise_if_cancelled(cancellation)
                _copy_verified_asset(
                    image.asset.path,
                    input_directory / f"{index:05d}.png",
                    image.asset.sha256,
                    cancellation,
                )
                _report(
                    report_progress,
                    index,
                    len(package.pages) + 1,
                    f"Página {index} preparada para KCC",
                )

            arguments = _conversion_arguments(
                executable,
                plan,
                package,
                input_directory,
                output_directory,
                profile,
            )
            _report(
                report_progress,
                len(package.pages),
                len(package.pages) + 1,
                "Gerando MOBI com KCC 13.0.4",
            )
            process = self._popen(
                arguments,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=workspace,
                close_fds=True,
            )
            self._wait_for_process(process, cancellation)
            _raise_if_cancelled(cancellation)
            source = _validated_mobi_output(output_directory, destination.name)
            os.replace(source, destination)
            size_bytes = destination.stat().st_size
            return GeneratedPackage(
                package_id=package.id,
                path=destination,
                sha256=_sha256_file(destination),
                size_bytes=size_bytes,
                page_count=len(package.pages),
            )
        except (KccAdapterError, KccWriteCancelled):
            destination.unlink(missing_ok=True)
            raise
        except subprocess.TimeoutExpired:
            destination.unlink(missing_ok=True)
            raise KccTimedOut("A conversão KCC excedeu o tempo máximo permitido.") from None
        except OSError:
            destination.unlink(missing_ok=True)
            raise KccConversionFailed("Não foi possível concluir a conversão KCC local.") from None
        finally:
            if workspace.exists() and not workspace.is_symlink():
                shutil.rmtree(workspace, ignore_errors=True)

    def _verify_executable(self, working_directory: Path) -> Path:
        if self._verified_executable is not None:
            return self._verified_executable
        path = self._executable_path
        try:
            if path.is_symlink() or not path.is_file():
                raise OSError
            resolved = path.resolve(strict=True)
        except OSError:
            raise KccExecutableUnavailable(
                "Selecione um executável KCC CLI existente e regular."
            ) from None
        try:
            result = self._run(
                [str(resolved), "--help"],
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=working_directory,
                timeout=_HELP_TIMEOUT_SECONDS,
                encoding="utf-8",
                errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired):
            raise KccExecutableUnavailable(
                "Não foi possível verificar a versão da CLI KCC selecionada."
            ) from None
        if result.returncode != 0:
            raise KccExecutableUnavailable("A CLI KCC selecionada não abriu a ajuda local.")
        version, options, formats = _parse_help(result.stdout)
        if (
            version != _VERIFIED_VERSION
            or not _REQUIRED_OPTIONS.issubset(options)
            or "MOBI" not in formats
        ):
            raise KccVersionUnsupported(
                "A versão/opções da CLI KCC não correspondem à versão 13.0.4 verificada."
            )
        self._verified_executable = resolved
        return resolved

    def _wait_for_process(
        self,
        process: subprocess.Popen[bytes],
        cancellation: CancellationPort | None,
    ) -> None:
        deadline = self._monotonic() + self._timeout_seconds
        while process.poll() is None:
            if cancellation is not None and cancellation.cancelled:
                _terminate_process(process)
                raise KccWriteCancelled("A exportação local foi cancelada.")
            if self._monotonic() >= deadline:
                _terminate_process(process)
                raise KccTimedOut("A conversão KCC excedeu o tempo máximo permitido.")
            self._sleep(min(_POLL_INTERVAL_SECONDS, max(0, deadline - self._monotonic())))
        if process.returncode != 0:
            raise KccConversionFailed("A CLI KCC terminou com erro na conversão local.")


def create_kcc_writer(executable_path: Path) -> KccCliWriter:
    """Factory tipada para a composição do caso de uso de exportação."""

    return KccCliWriter(executable_path)


def _parse_help(output: str) -> tuple[str | None, frozenset[str], frozenset[str]]:
    first_line = output.splitlines()[0] if output.splitlines() else ""
    version_match = re.match(r"comic2ebook v(\d+\.\d+\.\d+)(?:\s|$)", first_line)
    options = frozenset(re.findall(r"(?<![A-Za-z0-9])--[a-z][a-z0-9-]*", output))
    formats_match = re.search(
        r"Output format \(Available options: ([^)]*)\)", output, flags=re.IGNORECASE
    )
    formats = (
        frozenset(item.strip().upper() for item in formats_match.group(1).split(","))
        if formats_match is not None
        else frozenset()
    )
    return (version_match.group(1) if version_match else None), options, formats


def _profile_for_dimensions(width: object, height: object) -> str:
    if (width, height) == (600, 800):
        return "K810"
    if (width, height) == (1072, 1448):
        return "KPW34"
    raise KccProfileUnsupported(
        "MOBI com KCC 13.0.4 foi verificado para perfis 600 × 800 e 1072 × 1448."
    )


def _conversion_arguments(
    executable: Path,
    plan: ExportPlan,
    package: ExportPackagePlan,
    input_directory: Path,
    output_directory: Path,
    profile: str,
) -> list[str]:
    stem = Path(package.filename).stem
    arguments = [
        str(executable),
        "--profile",
        profile,
        "--format",
        "MOBI",
        "--cropping",
        "0",
        "--output",
        str(output_directory),
        "--title",
        package.title,
        "--filename",
        stem,
    ]
    if plan.direction is ReadingDirection.RIGHT_TO_LEFT:
        arguments.append("--manga-style")
    arguments.extend(("--author", plan.author or "", "--language", plan.language or ""))
    arguments.append(str(input_directory))
    return arguments


def _copy_verified_asset(
    source_path: Path,
    destination: Path,
    expected_sha256: str,
    cancellation: CancellationPort | None,
) -> None:
    if not source_path.is_absolute() or source_path.is_symlink() or not source_path.is_file():
        raise KccSourceChanged("Uma página processada não está disponível como arquivo regular.")
    digest = hashlib.sha256()
    try:
        with source_path.open("rb") as source, destination.open("xb") as target:
            while chunk := source.read(_COPY_CHUNK_BYTES):
                _raise_if_cancelled(cancellation)
                digest.update(chunk)
                target.write(chunk)
        if digest.hexdigest() != expected_sha256:
            destination.unlink(missing_ok=True)
            raise KccSourceChanged("Uma página processada mudou durante a conversão KCC.")
    except KccWriteCancelled:
        destination.unlink(missing_ok=True)
        raise
    except KccSourceChanged:
        raise
    except OSError:
        destination.unlink(missing_ok=True)
        raise KccSourceChanged("Uma página processada não pôde ser preparada para KCC.") from None


def _validated_mobi_output(output_directory: Path, expected_name: str) -> Path:
    try:
        entries = tuple(output_directory.iterdir())
        if len(entries) != 1:
            raise OSError
        result = entries[0]
        if (
            result.name.casefold() != expected_name.casefold()
            or result.suffix.casefold() != ".mobi"
            or result.is_symlink()
            or not result.is_file()
        ):
            raise OSError
        with result.open("rb") as stream:
            stream.seek(_MOBI_HEADER_OFFSET)
            signature = stream.read(len(_MOBI_SIGNATURE))
        if signature != _MOBI_SIGNATURE or result.stat().st_size < _MOBI_HEADER_OFFSET + 8:
            raise OSError
        return result
    except OSError:
        raise KccOutputInvalid("A CLI KCC não criou um arquivo MOBI válido.") from None


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _raise_if_cancelled(cancellation: CancellationPort | None) -> None:
    if cancellation is not None and cancellation.cancelled:
        raise KccWriteCancelled("A exportação local foi cancelada.")


def _report(
    callback: Callable[[int, int, str], None] | None,
    done: int,
    total: int,
    stage: str,
) -> None:
    if callback is not None:
        callback(done, total, stage)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
