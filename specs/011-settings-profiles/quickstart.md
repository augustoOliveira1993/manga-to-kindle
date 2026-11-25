# Quickstart de Validação — F011

**Pendente de aplicação persistente.**

1. `uv sync --locked`.
2. `uv run --locked pytest tests/unit/settings tests/integration/settings tests/ui/settings`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Instância limpa: confirmar built-ins/defaults; testar dimensões/margens 1 abaixo/no/acima e área útil.
5. Reiniciar 10 vezes; validar IDs/names/custom profiles and snapshots; migration defaults only on missing fields.
6. Com cache fixture, testar expiry/LRU/quota e paths ativos/unknown; checksum de originais/derivados/exports/credentials sentinel permanece.
7. Tentar reset cancelado/confirmado, paths inaccessible, tema/teclado; manter manual visual Win10/11 como pendente até executar.
