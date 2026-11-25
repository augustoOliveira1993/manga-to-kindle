# Quickstart de Validação — F007

**Pendente dos gates de licença/capacidade e instalação.**

1. `uv sync --locked` somente após revisão/aprovação EbookLib e lock compatível.
2. `uv run --locked pytest tests/unit/exports tests/integration/exports tests/security/exports`.
3. Validar fixtures com EPUBCheck da versão registrada; sem erros, validar capa/nav/idioma/identifier/spine/RTL, recursos locais e ausência de remote ref/script.
4. Rodar CBZ e divisão de tamanho com arquivos temporários; medir arquivo final, ordem e preservação de página inteira.
5. KCC: testes automatizados usam fake runner; teste binário real só após confirmação explícita de rede ou offline verificável e análise das opções da versão. Não rodar genericamente `--help` neste quickstart.
6. Manual em Kindle/Send to Kindle somente por pessoa autorizada, registrando checksum/modelo/firmware/rota; até lá a compatibilidade fixed layout permanece não verificada.
7. Ruff/MyPy: `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
