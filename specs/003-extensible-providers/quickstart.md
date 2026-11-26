# Quickstart de Validação — F003

**Estado**: fixture offline disponível; integração real bloqueada por `B003-REAL-SOURCE`.

## Preparar e executar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando inicia a aplicação. A consulta da fixture não requer acesso à internet.

## Roteiro de teste manual

1. Abra **Adicionar mangá**, informe `https://fixture.invalid/manga/demo` e consulte.
2. Confirme o título **A Biblioteca das Estrelas**, sete capítulos fictícios, a indicação de demonstração e a ordem `1, 1, 1.5, 2, 10`, seguida dos dois bônus.
3. Consulte novamente e confirme que a obra, os IDs e a ordem dos capítulos permanecem iguais. A numeração repetida representa capítulos distintos.
4. Informe `https://example.test/manga` e confirme que a aplicação informa que a fonte não é suportada, não atribui a ela os dados da fixture e continua responsiva. Se já há um catálogo válido na tela, ele permanece identificado como a última versão válida.
5. Informe `ftp://example.test/manga` e confirme a mensagem de URL/esquema inválido.
6. Volte à Biblioteca e confirme a navegação. Essa tela ainda mostra um exemplo visual fixo e não é a lista dos catálogos persistidos; a preservação de registros de outro provedor é verificada pela integração automatizada. Não apague o banco para limpar a fixture.

## Critérios que ainda precisam de validação manual

- Confirmar visualmente os rótulos de demonstração, as mensagens em português e a navegação por teclado no Windows 10/11.
- A integração automatizada confirma que a fixture não substitui nem altera um registro local de outro provedor.
- Confirmar que uma URL externa não suportada não produz atividade de rede; os testes automatizados já verificam a fronteira de socket.

Essas conferências manuais ficam registradas no [checkpoint de implementação](../implementation-checkpoint.md) e não bloqueiam o avanço para as próximas features.

## Validação automatizada

Testes focados da F003:

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_manga_provider.py tests/unit/application/test_provider_registry.py tests/unit/security/test_external_url_policy.py tests/unit/infrastructure/providers/test_fixture_provider.py tests/security/test_provider_url_policy.py tests/security/test_provider_log_redaction.py tests/integration/test_provider_authorization_gate.py tests/integration/test_provider_catalog_boundary.py -q
```

Os testes usam DNS/transporte injetáveis; cobrem IPv4/IPv6 privados, respostas DNS mistas, destino conectado diferente do validado, downgrade, loop e limite de redirecionamentos sem request real.

Validação de regressão e análise estática:

```powershell
uv run --locked --python 3.12 pytest -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Não há provedor real nem download real nesta feature.
