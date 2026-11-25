# Quickstart de Validação — F009

**SMTP habilita apenas depois de keyring Windows backend verificado; teste exclusivamente local.**

1. `uv sync --locked` após dependências F009 serem aprovadas e travadas.
2. `uv run --locked pytest tests/unit/transfers tests/integration/transfers tests/security/transfers`.
3. Fake vault + servidor SMTP local simulam TLS success/failure, auth, 4xx/5xx, limit, timeout/cancel pre-DATA e disconnect after DATA.
4. Confirmar que consent é por tentativa, tampered/missing export bloqueia, status unknown não retenta no restart, resposta positiva é “aceito pelo servidor”.
5. Buscar secret sentinel/email/path/title/body no DB/config/logs; zero ocorrências.
6. Testar abertura manual com fake OS launcher: pasta/URL abrem apenas após click; nenhum POST/anexo automático.
7. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.

Não conectar a SMTP público, conta Amazon ou Kindle durante testes automatizados.
