# Pesquisa — F005 Downloads

- A versão travada do projeto não inclui HTTPX. O transporte de produção usa `http.client`, sockets pinados e TLS da biblioteca padrão, sem proxy ambiental, com limites de leitura e cancelamento.
- NDL autoriza API/IIIF pontual para os itens individuais do corpus PDM; o endpoint IIIF observado redireciona algumas imagens a um host S3 exato. Redirects são limitados a cinco saltos e cada destino passa pela política F003, validação de DNS/IP e TLS; hosts diferentes são rejeitados.
- NDL entrega algumas imagens com `binary/octet-stream` apesar da URL IIIF `.jpg`. O transporte só aplica fallback MIME nesse caso; a assinatura JPEG, o decode e os limites continuam obrigatórios.
- Política de backoff fica na feature/provider. Retry-After é interpretado pelo adapter de protocolo e persistido como deadline; nunca reduzido pelo máximo do backoff local.
- Alembic/SQLAlchemy persistem job/tentativas e referências; file system não é a mesma transação do SQLite: usar staging, identificador de operação e reconciliação idempotente no startup.
- Pillow é usada somente para decodificação integral/verificação de dimensões; original recebido continua byte a byte intacto.
- O escopo de produção está limitado ao provider NDL autorizado; MangaDex e outras fontes continuam sob B003. Testes automatizados usam transporte in-memory/fake; o smoke real do item `851650` foi executado separadamente em perfil temporário.

Referências: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [HTTPX limits](https://www.python-httpx.org/advanced/resource-limits/), [HTTPX streaming/redirect differences](https://www.python-httpx.org/compatibility/), [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html), [Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html).
