import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from manga_to_kindle.infrastructure.persistence.database import (
    DatabaseClosedError,
    DatabaseMigrationError,
    SQLiteDatabase,
)
from manga_to_kindle.infrastructure.persistence.models import MangaRecord


def test_database_initializes_schema_and_reopens_idempotently(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "data" / "library.sqlite3")

    database.initialize()
    first_revision = database.current_revision()
    first_tables = set(inspect(database.engine).get_table_names())
    database.initialize()

    assert first_revision is not None
    assert database.current_revision() == first_revision
    assert {
        "manga",
        "chapter",
        "page",
        "download_job",
        "download_chapter",
        "download_page",
        "image_import_job",
        "processed_page",
        "device_profile",
        "export",
        "export_chapter",
        "alembic_version",
    } <= first_tables
    database.close()


def test_unit_of_work_commits_and_rolls_back(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    manga_id = uuid4()

    with database.unit_of_work() as session:
        session.add(MangaRecord(id=manga_id, title="Mangá de teste"))

    with pytest.raises(RuntimeError):
        with database.unit_of_work() as session:
            session.add(MangaRecord(id=uuid4(), title="Não persistir"))
            raise RuntimeError("falha injetada")

    with database.unit_of_work() as session:
        titles = session.scalars(select(MangaRecord.title)).all()

    assert titles == ["Mangá de teste"]
    database.close()


def test_foreign_keys_are_enabled_on_each_connection(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()

    with database.engine.connect() as connection:
        enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert enabled == 1
    database.close()


def test_failed_migration_restores_existing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "library.sqlite3"
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel VALUES ('preservado')")
        connection.commit()

    database = SQLiteDatabase(database_path)

    def fail_after_partial_change() -> None:
        with database.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE partial_migration (value TEXT)")
        raise RuntimeError("migration failure")

    monkeypatch.setattr(database, "_apply_migrations", fail_after_partial_change)

    with pytest.raises(DatabaseMigrationError):
        database.initialize()

    database.engine.dispose()
    with closing(sqlite3.connect(database_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        value = connection.execute("SELECT value FROM sentinel").fetchone()[0]

    assert "sentinel" in tables
    assert "partial_migration" not in tables
    assert value == "preservado"


def test_closed_database_rejects_new_units_of_work(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    database.close()

    with pytest.raises(DatabaseClosedError):
        with database.unit_of_work():
            pass
