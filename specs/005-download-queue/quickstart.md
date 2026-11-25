# Quickstart de Validação — F005

**Modo de validação**: transporte falso até autorização B003; não apontar para fonte real.

1. `uv sync --locked` depois de dependencies serem resolvidas.
2. `uv run --locked pytest tests/unit/downloads tests/integration/downloads tests/security/downloads tests/ui/downloads`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Fake clock testa retries e Retry-After; fake transport testa 408/429/5xx, erro terminal, stream >25 MiB, pixel >50 MP, MIME/signature/decode inválidos.
5. Interromper processo entre arquivo `.part`, rename e commit; reiniciar DB/files temporários e conferir recuperação, sem auto-rede.
6. Assert concorrência máxima 2, ordem estável, pause/cancel ≤200 ms e logs sem URLs/segredos.
