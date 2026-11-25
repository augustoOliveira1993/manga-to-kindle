# Pesquisa — F005 Downloads

- HTTPX permite timeouts por tipo e pool `Limits`; timeout deve refletir spec (connect/read), limite de connections condicionado a scheduler e redirects ficam false. Streaming usa `Client.stream`/`iter_bytes`, fechar sempre, impondo teto durante leitura.
- HTTPX não define a política de backoff comercial; política explicitada pela spec e provider. Retry-After é interpretado pelo adapter de protocolo e persistido como deadline; nunca reduzido pelo máximo do backoff local.
- Alembic/SQLAlchemy persistem job/tentativas e referências; file system não é a mesma transação do SQLite: usar staging, identificador de operação e reconciliação idempotente no startup.
- Pillow é usada somente para decodificação integral/verificação de dimensões; original recebido continua byte a byte intacto.
- Como F003 não tem fonte autorizada, HTTPX fica fora do caminho de produção até B003 ser removido por evidência/revisão. Testes usam transporte in-memory/fake.

Referências: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [HTTPX limits](https://www.python-httpx.org/advanced/resource-limits/), [HTTPX streaming/redirect differences](https://www.python-httpx.org/compatibility/), [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html), [Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html).
