import os
from pathlib import Path

from manga_to_kindle.infrastructure.paths import AppPaths


def test_user_paths_are_created_idempotently(tmp_path: Path) -> None:
    paths = AppPaths.from_root(tmp_path / "dados locais")

    paths.ensure()
    paths.ensure()

    assert paths.root == tmp_path / "dados locais"
    assert paths.config.is_dir()
    assert paths.data.is_dir()
    assert paths.logs.is_dir()
    assert paths.cache.is_dir()


def test_qstandardpaths_resolves_application_local_data(
    qt_core_app: object,
) -> None:
    paths = AppPaths.from_qstandardpaths()

    assert paths.root.is_absolute()
    assert paths.root.name == "MangaToKindleTests"
    assert paths.root != Path.cwd()
    if os.name == "nt":
        local_app_data = Path(os.environ["LOCALAPPDATA"]).resolve()
        assert paths.root.is_relative_to(local_app_data)
