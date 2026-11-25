# Quickstart de Validação — F010

**B003 ativo: simulação apenas.**

1. `uv sync --locked` após F001.
2. `uv run --locked pytest tests/unit/updates tests/integration/updates tests/ui/updates`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Com fake clock: desabilitado → zero calls; enabled → um call no due; suspension/restart → sem catch-up burst; desabilitar/cancel → sem próximos checks.
5. Com provider fixture: catálogo novo com IDs novos/duplicados/renomeados, erro parcial, indisponibilidade/limit; manter snapshot em falha e notificações únicas para IDs estáveis.
6. Confirmar que notice não cria DownloadJob/TransferJob e que nenhum fixture faz DNS/socket.
