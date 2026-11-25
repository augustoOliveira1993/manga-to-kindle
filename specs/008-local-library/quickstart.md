# Quickstart de Validação — F008

**Pendente de F001/F008 code e database migrations.**

1. `uv sync --locked`.
2. `uv run --locked pytest tests/unit/library tests/integration/persistence tests/security/library`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Criar DB temporário blank, aplicar revisões, inserir relações e validar FK, unique IDs, rollback e restart/reopen.
5. Exercitar busca acento/case/filtros/favoritos/ordem/histórico e dois arquivos faltantes.
6. Simular falha entre rename de arquivo e commit; confirmar recovery. Testar exclusão cancelada, registro-only e escopo explícito; confirmar arquivo externo nunca removido.
