# Quickstart de Validação — F003

**Atual**: fixture offline; integração real bloqueada por B003.

1. Após ambiente F001: `uv sync --locked`.
2. `uv run --locked pytest tests/unit/domain/test_manga_provider.py tests/unit/application/test_provider_registry.py tests/unit/security/test_external_url_policy.py tests/unit/infrastructure/providers/test_fixture_provider.py tests/security/test_provider_url_policy.py tests/security/test_provider_log_redaction.py tests/integration/test_provider_authorization_gate.py tests/integration/test_provider_catalog_boundary.py -q`.
3. Verificar URL sintética `https://fixture.invalid/manga/demo` (mesmos IDs, zero DNS/socket); inputs inválidos, userinfo, fontes não registradas e hosts externos são recusados sem fallback.
4. Os testes injetam resolução DNS e respostas de redirect; cobrem IPv4/IPv6 privados, reservados, respostas mistas e destino alterado, além de downgrade, loop e limites antes de qualquer conexão real.
5. `uv run --locked ruff check src/manga_to_kindle tests`; `uv run --locked mypy src/manga_to_kindle`.

Não executar request real em qualquer passo.
