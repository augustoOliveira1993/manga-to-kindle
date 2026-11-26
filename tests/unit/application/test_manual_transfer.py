from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from manga_to_kindle.application.transfers.open_manual_flow import (
    ArtifactUnavailable,
    OpenManualSend,
)
from manga_to_kindle.domain.transfers import ExportTransferArtifact


class ArtifactRepository:
    def __init__(self, artifact: ExportTransferArtifact | None) -> None:
        self.artifact = artifact

    def get_artifact(self, artifact_id):
        if self.artifact is not None and self.artifact.id == artifact_id:
            return self.artifact
        return None


class SystemOpener:
    def __init__(self, *, directory_ok: bool = True, url_ok: bool = True) -> None:
        self.directory_ok = directory_ok
        self.url_ok = url_ok
        self.directories: list[Path] = []
        self.urls: list[str] = []

    def open_directory(self, path: Path) -> bool:
        self.directories.append(path)
        return self.directory_ok

    def open_url(self, url: str) -> bool:
        self.urls.append(url)
        return self.url_ok


def _artifact(path: Path, data: bytes | None = None) -> ExportTransferArtifact:
    content = data if data is not None else path.read_bytes()
    return ExportTransferArtifact(
        id=uuid4(),
        export_id=uuid4(),
        package_id=uuid4(),
        format="epub",
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )


def test_manual_flow_opens_exact_folder_and_official_page_after_validating_epub(
    tmp_path: Path,
) -> None:
    output = tmp_path / "manga.epub"
    output.write_bytes(b"real fixture epub bytes")
    artifact = _artifact(output)
    opener = SystemOpener()

    result = OpenManualSend(ArtifactRepository(artifact), opener).execute(artifact.id)

    assert result.artifact == artifact
    assert result.directory_opened is True
    assert result.page_opened is True
    assert opener.directories == [tmp_path]
    assert opener.urls == ["https://www.amazon.com/sendtokindle"]


@pytest.mark.parametrize("tamper", ["changed", "missing", "size"])
def test_manual_flow_blocks_missing_or_changed_artifact_without_opening_system_apps(
    tmp_path: Path,
    tamper: str,
) -> None:
    output = tmp_path / "manga.epub"
    output.write_bytes(b"original")
    artifact = _artifact(output)
    if tamper == "changed":
        output.write_bytes(b"modified")
    elif tamper == "missing":
        output.unlink()
    else:
        artifact = ExportTransferArtifact(
            id=artifact.id,
            export_id=artifact.export_id,
            package_id=artifact.package_id,
            format=artifact.format,
            path=artifact.path,
            sha256=artifact.sha256,
            size_bytes=artifact.size_bytes + 1,
        )
    opener = SystemOpener()

    with pytest.raises(ArtifactUnavailable):
        OpenManualSend(ArtifactRepository(artifact), opener).execute(artifact.id)

    assert opener.directories == []
    assert opener.urls == []


def test_manual_flow_reports_folder_and_browser_failures_separately(tmp_path: Path) -> None:
    output = tmp_path / "manga.epub"
    output.write_bytes(b"valid epub")
    artifact = _artifact(output)
    opener = SystemOpener(directory_ok=False, url_ok=True)

    result = OpenManualSend(ArtifactRepository(artifact), opener).execute(artifact.id)

    assert result.directory_opened is False
    assert result.page_opened is True


def test_manual_flow_refuses_cbz_even_when_its_bytes_are_intact(tmp_path: Path) -> None:
    output = tmp_path / "manga.cbz"
    output.write_bytes(b"valid cbz")
    artifact = _artifact(output)
    artifact = ExportTransferArtifact(
        id=artifact.id,
        export_id=artifact.export_id,
        package_id=artifact.package_id,
        format="cbz",
        path=artifact.path,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
    )
    opener = SystemOpener()

    with pytest.raises(ArtifactUnavailable):
        OpenManualSend(ArtifactRepository(artifact), opener).execute(artifact.id)

    assert opener.directories == []
    assert opener.urls == []
