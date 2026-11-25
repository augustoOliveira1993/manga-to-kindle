# Quickstart de Validação — F004

1. `uv sync --locked`.
2. `uv run --locked pytest tests/unit/domain/test_catalog_models.py tests/unit/domain/test_chapter_ordering.py tests/unit/application/test_get_catalog.py tests/unit/application/test_chapter_selection.py tests/integration/test_catalog_refresh.py tests/integration/test_catalog_fixture_flow.py tests/integration/test_provider_catalog_boundary.py tests/ui/test_add_manga_view.py tests/ui/test_chapter_selection_view.py -q`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Consultar `https://fixture.invalid/manga/demo`; confirmar título fictício, campos opcionais ausentes sem inferência, IDs estáveis, ordenação decimal/especial e seleção inclusiva.
5. Injetar falha e cancelamento; confirmar último snapshot íntegro, retentativa disponível e zero sockets/rede. A URL externa não registrada deve resultar em mensagem de fonte não suportada, sem exibir catálogo de fixture.

A aplicação consulta e persiste a fixture local em worker, sem acesso de rede. A capa permanece neutra quando não há arquivo local; capítulos não são baixados nesta feature.
