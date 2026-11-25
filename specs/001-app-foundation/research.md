# Pesquisa — F001 Fundação

## Decisões

- Diretórios locais: `QStandardPaths.AppLocalDataLocation` para raiz da aplicação e subpastas `config`, `data`, `logs`, `cache`; fora da instalação.
- Logs: `logging.handlers.RotatingFileHandler`, UTF-8, `maxBytes=5*1024*1024`, `backupCount=3`; ambos diferentes de zero ativam rotação conforme Python 3.12. Redação antes de materializar traceback.
- Persistência compartilhada: SQLAlchemy 2 declarative mappings + Alembic. Para DDL SQLite que precise reconstruir tabela, usar batch mode “move and copy”; backup validado antes de migrações complexas.
- Pydantic v2 apenas na fronteira de configuração/JSON se validadores e schema justificarem; domínio fica em dataclasses/value objects tipados simples.
- Qt: worker `QObject` movido a `QThread` e sinais queued; o objeto QThread continua com affinity da thread que o criou. Startup de disco precisa terminar antes de mostrar janela ou ficar em worker inicial.
- `uv sync --locked` / `uv run --locked` candidatos ao setup após existir projeto e lock; não executados agora.

## Fontes primárias

- [Python 3.12 RotatingFileHandler](https://docs.python.org/3.12/library/logging.handlers.html)
- [Qt for Python: QStandardPaths](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QStandardPaths.html)
- [Qt for Python: QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
- [SQLAlchemy 2 Declarative Tables](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
- [Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [uv: locking e syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Pydantic: JSON Schema](https://pydantic.dev/docs/validation/latest/concepts/json_schema/)

## Pendências

Não existe ambiente/lock para confirmar versão e compatibilidade Windows; escolher com documentação oficial e registrar em `uv.lock` na implementação F001.
