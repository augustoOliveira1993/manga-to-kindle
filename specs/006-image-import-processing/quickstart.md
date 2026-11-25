# Quickstart de Validação — F006

**Pendente de implementação/Pillow lock.**

1. `uv sync --locked` em Windows 10/11; confirmar Pillow e suporte efetivo WEBP/EXIF no ambiente travado.
2. `uv run --locked pytest tests/unit/images tests/integration/images tests/security/images tests/ui/images`.
3. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.
4. Importar fixtures de pasta/CBZ com 1/2/10, JPEG/PNG/WEBP; validar hash original antes/depois, EXIF, alpha, escala de cinza, 600×800, proporção.
5. Testar path traversal, UNC/drive, symlink, colisão Windows, criptografia, limites abaixo/no/acima, disco cheio, cancellation e reimport idempotente.
6. Confirmar crop/split desligados, preview fiel ao output e nenhum request/rede/transferência.
