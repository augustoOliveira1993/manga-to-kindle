import socket
from pathlib import Path

import pytest

from manga_to_kindle.application.bootstrap import bootstrap_application
from manga_to_kindle.infrastructure.config.settings import InvalidSettingsError
from manga_to_kindle.infrastructure.paths import AppPaths


def test_startup_creates_and_reuses_local_state_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_network(*_: object, **__: object) -> None:
        raise AssertionError("a fundação não pode abrir conexões de rede")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    paths = AppPaths.from_root(tmp_path / "perfil local")

    first = bootstrap_application(paths)
    first_revision = first.database.current_revision()
    first.shutdown()
    second = bootstrap_application(paths)

    assert second.database.current_revision() == first_revision
    assert paths.database_file.is_file()
    assert paths.config.is_dir()
    assert paths.data.is_dir()
    assert paths.logs.is_dir()
    assert paths.cache.is_dir()
    second.shutdown()


def test_startup_preserves_invalid_configuration_and_fails_closed(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path)
    paths.ensure()
    original = b'{"log_backup_count": 0}\n'
    paths.settings_file.write_bytes(original)

    with pytest.raises(InvalidSettingsError):
        bootstrap_application(paths)

    assert paths.settings_file.read_bytes() == original
