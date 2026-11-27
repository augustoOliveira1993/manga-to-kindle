from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from tests.export_support import fixture_sources, make_request

from manga_to_kindle.application.exports.plan import PlanExport
from manga_to_kindle.domain.exports import ExportFormat
from manga_to_kindle.domain.image_processing import ReadingDirection
from manga_to_kindle.infrastructure.exports.kcc_adapter import (
    KccCliWriter,
    KccConversionFailed,
    KccExecutableUnavailable,
    KccLanguageRequired,
    KccOutputInvalid,
    KccProfileUnsupported,
    KccSizeLimitUnsupported,
    KccTimedOut,
    KccVersionUnsupported,
    KccWriteCancelled,
    _parse_help,
    _profile_for_dimensions,
)

_HELP_PATH = Path(__file__).parents[2] / "fixtures" / "kcc" / "13.0.4-windows-amd64-help.txt"
_HELP = _HELP_PATH.read_text(encoding="utf-8")
_MOBI = bytes(60) + b"BOOKMOBI" + bytes(32)


def test_captured_official_help_declares_the_verified_kcc_version_and_options() -> None:
    version, options, formats = _parse_help(_HELP)

    assert version == "13.0.4"
    assert {"--profile", "--format", "--cropping", "--output", "--title", "--filename"} <= options
    assert {"EPUB", "MOBI", "CBZ"} <= formats


def test_kcc_copies_verified_pages_and_builds_argument_list_without_shell(
    tmp_path: Path,
) -> None:
    executable = _fake_executable(tmp_path)
    plan = _mobi_plan(tmp_path)
    package = plan.packages[0]
    stage = tmp_path / "stage"
    stage.mkdir()
    destination = stage / package.filename
    called: dict[str, object] = {}

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        called["help_args"] = args
        called["help_kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0, _HELP, "")

    def popen(args: list[str], **kwargs: object) -> _FinishedProcess:
        called["conversion_args"] = args
        called["conversion_kwargs"] = kwargs
        output_directory = Path(args[args.index("--output") + 1])
        output_directory.joinpath(f"{args[args.index('--filename') + 1]}.mobi").write_bytes(
            _MOBI
        )
        return _FinishedProcess()

    originals = tuple(page.asset.path.read_bytes() for page in package.pages)
    writer = KccCliWriter(executable, run=run, popen=popen)

    result = writer.write(plan, package, destination)

    assert result.path == destination
    assert result.page_count == len(package.pages)
    assert result.size_bytes == len(_MOBI)
    assert destination.read_bytes() == _MOBI
    assert tuple(page.asset.path.read_bytes() for page in package.pages) == originals
    args = called["conversion_args"]
    assert isinstance(args, list)
    assert args[args.index("--profile") + 1] == "K810"
    assert args[args.index("--format") + 1] == "MOBI"
    assert args[args.index("--author") + 1] == ""  # KCC's default author is not accepted.
    assert args[args.index("--language") + 1] == "pt-BR"
    assert "--manga-style" in args
    assert "--delete" not in args
    assert args[-1].endswith("input")
    assert called["conversion_kwargs"]["shell"] is False
    assert called["help_kwargs"]["shell"] is False
    assert not (stage / "kcc-work").exists()


def test_kcc_selects_the_verified_paperwhite_profile_for_1072_by_1448() -> None:
    assert _profile_for_dimensions(1072, 1448) == "KPW34"


def test_kcc_rejects_missing_executable_and_unverified_versions(tmp_path: Path) -> None:
    missing = KccCliWriter(tmp_path / "missing.exe")
    plan = _mobi_plan(tmp_path)
    stage = tmp_path / "stage"
    stage.mkdir()

    with pytest.raises(KccExecutableUnavailable):
        missing.write(plan, plan.packages[0], stage / plan.packages[0].filename)

    executable = _fake_executable(tmp_path)
    unknown_help = _HELP.replace("comic2ebook v13.0.4", "comic2ebook v99.0.0", 1)
    writer = KccCliWriter(
        executable,
        run=lambda args, **kwargs: subprocess.CompletedProcess(args, 0, unknown_help, ""),
        popen=lambda *_args, **_kwargs: pytest.fail("Não deve executar uma versão desconhecida"),
    )
    with pytest.raises(KccVersionUnsupported):
        writer.write(plan, plan.packages[0], stage / plan.packages[0].filename)


def test_kcc_rejects_dimensions_not_verified_for_mobi() -> None:
    with pytest.raises(KccProfileUnsupported):
        _profile_for_dimensions(1404, 1872)


def test_kcc_requires_explicit_language_and_rejects_unverified_size_splitting(
    tmp_path: Path,
) -> None:
    executable = _fake_executable(tmp_path)
    plan = _mobi_plan(tmp_path)
    package = plan.packages[0]
    stage = tmp_path / "stage"
    stage.mkdir()
    writer = KccCliWriter(executable, run=_help_runner)

    with pytest.raises(KccLanguageRequired):
        writer.write(replace(plan, language=None), package, stage / package.filename)
    with pytest.raises(KccSizeLimitUnsupported):
        writer.write(replace(plan, max_size_bytes=1024), package, stage / package.filename)


def test_kcc_rejects_exit_failure_and_invalid_output(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path)
    plan = _mobi_plan(tmp_path)
    package = plan.packages[0]
    stage = tmp_path / "stage"
    stage.mkdir()

    failed_process = KccCliWriter(
        executable,
        run=_help_runner,
        popen=lambda *_args, **_kwargs: _FinishedProcess(returncode=2),
    )
    with pytest.raises(KccConversionFailed):
        failed_process.write(plan, package, stage / package.filename)

    def invalid_output(args: list[str], **_kwargs: object) -> _FinishedProcess:
        output_directory = Path(args[args.index("--output") + 1])
        output_directory.joinpath(f"{args[args.index('--filename') + 1]}.mobi").write_bytes(
            b"not a MOBI file"
        )
        return _FinishedProcess()

    invalid = KccCliWriter(executable, run=_help_runner, popen=invalid_output)
    with pytest.raises(KccOutputInvalid):
        invalid.write(plan, package, stage / package.filename)
    assert not (stage / package.filename).exists()


def test_kcc_timeout_terminates_the_external_process(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path)
    plan = _mobi_plan(tmp_path)
    package = plan.packages[0]
    stage = tmp_path / "stage"
    stage.mkdir()
    clock = [0.0]
    process = _HangingProcess()
    writer = KccCliWriter(
        executable,
        timeout_seconds=0.15,
        run=_help_runner,
        popen=lambda *_args, **_kwargs: process,
        monotonic=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )

    with pytest.raises(KccTimedOut):
        writer.write(plan, package, stage / package.filename)

    assert process.terminated
    assert not (stage / package.filename).exists()


def test_kcc_cancellation_terminates_process_and_preserves_source_pages(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path)
    plan = _mobi_plan(tmp_path)
    package = plan.packages[0]
    stage = tmp_path / "stage"
    stage.mkdir()
    clock = [0.0]
    process = _HangingProcess()

    class Cancellation:
        @property
        def cancelled(self) -> bool:
            return clock[0] >= 0.1

    writer = KccCliWriter(
        executable,
        run=_help_runner,
        popen=lambda *_args, **_kwargs: process,
        monotonic=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    originals = tuple(page.asset.path.read_bytes() for page in package.pages)

    with pytest.raises(KccWriteCancelled):
        writer.write(plan, package, stage / package.filename, cancellation=Cancellation())

    assert process.terminated
    assert not (stage / package.filename).exists()
    assert tuple(page.asset.path.read_bytes() for page in package.pages) == originals


def _mobi_plan(tmp_path: Path):
    sources = fixture_sources()
    request = replace(
        make_request(sources, chapter_indexes=(0,), format=ExportFormat.MOBI),
        output_directory=tmp_path.resolve(),
        direction=ReadingDirection.RIGHT_TO_LEFT,
    )
    return PlanExport().execute(sources, request)


def _fake_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "kcc.exe"
    executable.write_bytes(b"test only")
    return executable


def _help_runner(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, 0, _HELP, "")


class _FinishedProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode

    def poll(self) -> int:
        return self.returncode


class _HangingProcess:
    returncode: int | None = None

    def __init__(self) -> None:
        self.terminated = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout: float | None = None) -> int:
        return -15

    def kill(self) -> None:
        self.returncode = -9
