# Pesquisa — F008 Biblioteca

## Decisões

- SQLAlchemy 2 declarative mapped classes (`DeclarativeBase`, `Mapped`, `mapped_column`) in infrastructure; domain never stores ORM entities.
- `Session` is a stateful transaction and not shared among concurrent threads/tasks. UI read and background worker use separate short-lived sessions; DTO/projection crosses signals, not Session-bound instances.
- SQLite foreign key pragma must be configured on every connection. Unit-of-work transaction boundaries wrap catalog batch changes; DB and filesystem use staging/reconciliation because there is no shared transaction.
- Alembic batch operations use move/copy for SQLite DDL lacking ALTER support. Generated autogenerate migration is a candidate and must be reviewed.
- SQLite backup (`Connection.backup`) is available for online consistent backup; use before data migration/release, validate and retain until new schema accepted.
- Library query uses normal indexed SQL; do not add FTS or another DB until measured search requirement warrants it.

## Referências primárias

- [SQLAlchemy 2 declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
- [SQLAlchemy 2 session basics/thread safety](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [SQLAlchemy SQLite dialect / foreign keys](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Alembic batch migration](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [Python sqlite3 backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)

Versões compatíveis com Python 3.12, SQLAlchemy/Alembic e Windows ficam a confirmar no primeiro lock; não há metadata de projeto ainda.
