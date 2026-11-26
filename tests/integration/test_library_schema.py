from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from manga_to_kindle.infrastructure.persistence.database import SQLiteDatabase
from manga_to_kindle.infrastructure.persistence.models import ChapterRecord, MangaRecord


def test_library_migration_preserves_catalog_and_enforces_favorites_and_foreign_keys(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "library.sqlite3"
    prior = SQLiteDatabase(database_path)
    prior.initialize()
    manga_id = UUID("b27a57b5-fc34-47ca-982e-89db905df8d2")
    chapter_id = UUID("328a322e-1eca-4ad9-96b4-6e702608f2a3")
    with prior.unit_of_work() as session:
        session.add(MangaRecord(id=manga_id, title="Coração Azul", provider_id="fixture"))
        session.add(
            ChapterRecord(
                id=chapter_id,
                manga_id=manga_id,
                title="A chegada",
                number="1",
                position=0,
            )
        )
    prior.close()

    upgraded = SQLiteDatabase(database_path)
    upgraded.initialize()
    with upgraded.unit_of_work() as session:
        manga = session.get(MangaRecord, manga_id)
        chapter = session.get(ChapterRecord, chapter_id)
        with upgraded.engine.connect() as connection:
            foreign_key_violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            foreign_keys_enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert upgraded.current_revision() == "0007_transfers"
    assert manga is not None and manga.title == "Coração Azul" and manga.favorite is False
    assert chapter is not None and chapter.title == "A chegada" and chapter.favorite is False
    assert foreign_keys_enabled == 1
    assert foreign_key_violations == []
    assert {"library_preference", "library_deletion_plan", "library_asset"} <= set(
        inspect(upgraded.engine).get_table_names()
    )
    upgraded.close()


def test_library_foreign_keys_reject_orphan_records_on_each_connection(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "library.sqlite3")
    database.initialize()
    with database.engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        try:
            connection.exec_driver_sql(
                "INSERT INTO chapter (id, manga_id, title, number, position, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "bdf2ef7d-1177-4f6b-b7c6-06d565133866",
                    "e4d06b6e-5a55-4aa9-a5a6-27b9e3238d60",
                    "Órfão",
                    "1",
                    0,
                    "2026-11-26 00:00:00",
                ),
            )
        except IntegrityError:
            pass
        else:
            raise AssertionError("A conexão SQLite aceitou um capítulo órfão.")
    database.close()
