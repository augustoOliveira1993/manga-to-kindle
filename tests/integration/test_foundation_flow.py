import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import text

from manga_to_kindle.application.bootstrap import bootstrap_application
from manga_to_kindle.infrastructure.paths import AppPaths
from manga_to_kindle.infrastructure.persistence.database import (
    DatabaseMigrationError,
    SQLiteDatabase,
)


def test_migration_failure_restores_existing_file_and_allows_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = AppPaths.from_root(tmp_path / "perfil")
    paths.ensure()
    with closing(sqlite3.connect(paths.database_file)) as connection:
        connection.execute("CREATE TABLE legacy_data (value TEXT NOT NULL)")
        connection.execute("INSERT INTO legacy_data VALUES ('conteúdo preservado')")
        connection.commit()

    def fail_after_partial_change(database: SQLiteDatabase) -> None:
        with database.engine.begin() as connection:
            connection.execute(text("CREATE TABLE partial_change (value TEXT)"))
        raise RuntimeError("erro com detalhe interno")

    with monkeypatch.context() as scoped:
        scoped.setattr(SQLiteDatabase, "_apply_migrations", fail_after_partial_change)
        with pytest.raises(DatabaseMigrationError):
            bootstrap_application(paths)

    with closing(sqlite3.connect(paths.database_file)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        value = connection.execute("SELECT value FROM legacy_data").fetchone()[0]

    assert "legacy_data" in tables
    assert "partial_change" not in tables
    assert value == "conteúdo preservado"

    runtime = bootstrap_application(paths)
    assert runtime.database.current_revision() is not None
    with runtime.database.engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM legacy_data")).scalar_one() == value
    runtime.shutdown()
