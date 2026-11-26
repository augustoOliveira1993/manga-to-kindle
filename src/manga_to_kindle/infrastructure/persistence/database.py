"""SQLite engine, unidade de trabalho e execução recuperável de migrações."""

from __future__ import annotations

import os
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Engine, create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


class DatabaseInitializationError(RuntimeError):
    """Falha na abertura ou validação da base local."""

    code = "DATABASE_INITIALIZATION_FAILED"


class DatabaseMigrationError(RuntimeError):
    """Migração falhou; os dados prévios foram restaurados quando possível."""

    code = "DATABASE_MIGRATION_FAILED"


class DatabaseRecoveryError(RuntimeError):
    """Falha ao restaurar o backup de migração."""

    code = "DATABASE_RECOVERY_FAILED"


class DatabaseClosedError(RuntimeError):
    """Operação recusada depois de iniciar o encerramento da base."""

    code = "DATABASE_CLOSED"


class DatabaseBusyError(RuntimeError):
    """Há unidades de trabalho ativas além do limite de encerramento."""

    code = "DATABASE_BUSY_DURING_SHUTDOWN"


class SQLiteDatabase:
    """Acesso tipado a SQLite com uma sessão isolada por unidade de trabalho."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = self._create_engine(database_path)
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )
        self._condition = threading.Condition()
        self._active_units = 0
        self._closing = False
        self._initialized = False

    @staticmethod
    def _create_engine(database_path: Path) -> Engine:
        url = URL.create("sqlite+pysqlite", database=str(database_path))
        engine = create_engine(url, connect_args={"timeout": 5.0, "check_same_thread": False})

        @event.listens_for(engine, "connect")
        def enable_sqlite_safety(dbapi_connection: sqlite3.Connection, _: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        return engine

    def initialize(self) -> None:
        """Aplica migrações pendentes sem expor a janela a um esquema parcial."""
        with self._condition:
            if self._closing:
                raise DatabaseClosedError("A base está encerrando.")
            if self._initialized:
                return

        had_database = self.database_path.exists() and self.database_path.stat().st_size > 0
        backup_path: Path | None = None
        try:
            current_revision = self.current_revision()
            target_revision = self._head_revision()
            if current_revision == target_revision:
                self._verify_integrity()
                self._initialized = True
                return

            if had_database:
                backup_path = self._create_backup()
            self._apply_migrations()
            self._verify_integrity()
            if self.current_revision() != target_revision:
                raise DatabaseMigrationError("A base não chegou à revisão esperada.")
            self._initialized = True
        except DatabaseMigrationError:
            self._recover_after_migration_failure(had_database, backup_path)
            raise
        except (OSError, SQLAlchemyError, sqlite3.Error) as exc:
            self._recover_after_migration_failure(had_database, backup_path)
            raise DatabaseMigrationError("Não foi possível aplicar as migrações locais.") from exc
        except Exception as exc:
            self._recover_after_migration_failure(had_database, backup_path)
            raise DatabaseMigrationError("A migração local foi interrompida e revertida.") from exc

    def current_revision(self) -> str | None:
        with self.engine.connect() as connection:
            if "alembic_version" not in inspect(connection).get_table_names():
                return None
            return connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()

    @contextmanager
    def unit_of_work(self) -> Iterator[Session]:
        with self._condition:
            if self._closing:
                raise DatabaseClosedError("A base está encerrando.")
            self._active_units += 1

        session: Session | None = None
        try:
            session = self._session_factory()
            yield session
            session.commit()
        except Exception:
            if session is not None:
                session.rollback()
            raise
        finally:
            if session is not None:
                session.close()
            with self._condition:
                self._active_units -= 1
                self._condition.notify_all()

    def close(self, timeout_seconds: float = 10.0) -> None:
        """Recusa trabalho novo e aguarda unidades existentes antes de liberar o engine."""
        with self._condition:
            self._closing = True
            finished = self._condition.wait_for(
                lambda: self._active_units == 0,
                timeout=timeout_seconds,
            )
        if not finished:
            raise DatabaseBusyError("Há operações locais que ainda não terminaram.")
        self.engine.dispose()

    def _head_revision(self) -> str:
        config = self._migration_config()
        head = ScriptDirectory.from_config(config).get_current_head()
        if head is None:
            raise DatabaseMigrationError("O pacote do aplicativo não contém migrações.")
        return head

    def _migration_config(self) -> Config:
        config = Config()
        script_directory = Path(__file__).parent / "migrations"
        config.set_main_option("script_location", str(script_directory).replace("%", "%%"))
        return config

    def _apply_migrations(self) -> None:
        config = self._migration_config()
        with self.engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def _verify_integrity(self) -> None:
        with self.engine.connect() as connection:
            result: str = connection.exec_driver_sql(
                "PRAGMA integrity_check"
            ).scalar_one()
            foreign_key_violations = connection.exec_driver_sql(
                "PRAGMA foreign_key_check"
            ).all()
        if result != "ok":
            raise DatabaseInitializationError("A verificação de integridade do SQLite falhou.")
        if foreign_key_violations:
            raise DatabaseInitializationError(
                "A verificação de relações do banco local encontrou registros órfãos."
            )

    def _create_backup(self) -> Path:
        backup_path = self.database_path.with_name(
            f"{self.database_path.name}.migration-backup"
        )
        temporary_path = backup_path.with_name(f".{backup_path.name}.{uuid4().hex}.tmp")
        try:
            with closing(sqlite3.connect(self.database_path)) as source:
                with closing(sqlite3.connect(temporary_path)) as destination:
                    source.backup(destination)
                    destination.commit()
            os.replace(temporary_path, backup_path)
            return backup_path
        except (OSError, sqlite3.Error) as exc:
            temporary_path.unlink(missing_ok=True)
            raise DatabaseMigrationError("Não foi possível criar o backup de segurança.") from exc

    def _recover_after_migration_failure(
        self, had_database: bool, backup_path: Path | None
    ) -> None:
        self.engine.dispose()
        if had_database and backup_path is not None and backup_path.exists():
            restore_path = self.database_path.with_name(
                f".{self.database_path.name}.{uuid4().hex}.restore"
            )
            try:
                shutil.copyfile(backup_path, restore_path)
                with restore_path.open("r+b") as stream:
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(restore_path, self.database_path)
            except OSError as exc:
                restore_path.unlink(missing_ok=True)
                raise DatabaseRecoveryError(
                    "A migração falhou e o backup automático precisa de recuperação manual."
                ) from exc
        elif not had_database:
            for candidate in (
                self.database_path,
                Path(f"{self.database_path}-wal"),
                Path(f"{self.database_path}-shm"),
            ):
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    pass
