from __future__ import annotations

import hashlib
import socket
from pathlib import Path
from uuid import uuid4

from manga_to_kindle.application.transfers.open_manual_flow import OpenManualSend
from manga_to_kindle.domain.transfers import ExportTransferArtifact


class ArtifactRepository:
    def __init__(self, artifact: ExportTransferArtifact) -> None:
        self.artifact = artifact

    def get_artifact(self, artifact_id):
        return self.artifact if artifact_id == self.artifact.id else None


class FakeSystemOpener:
    def open_directory(self, _path: Path) -> bool:
        return True

    def open_url(self, _url: str) -> bool:
        return True


def test_manual_send_does_not_open_network_or_upload(tmp_path: Path, monkeypatch) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("o fluxo manual não pode abrir uma conexão de rede")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    path = tmp_path / "chapter.epub"
    path.write_bytes(b"synthetic local EPUB bytes")
    artifact = ExportTransferArtifact(
        id=uuid4(),
        export_id=uuid4(),
        package_id=uuid4(),
        format="epub",
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        size_bytes=path.stat().st_size,
    )

    result = OpenManualSend(
        ArtifactRepository(artifact),
        FakeSystemOpener(),
    ).execute(artifact.id)

    assert result.directory_opened
    assert result.page_opened
