# Quickstart de Validação — F004

# Quickstart de Validação — F004

**Estado**: catálogo offline com seleção e refresh recuperável; fontes reais, download de capítulos e capas remotas estão fora do escopo.

## Preparar e executar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando inicia a aplicação. A fixture não requer internet e os capítulos não são baixados.

## Roteiro de teste manual

1. Abra **Adicionar mangá**, informe `https://fixture.invalid/manga/demo` e consulte o catálogo.
2. Confirme o título **A Biblioteca das Estrelas**, a indicação de demonstração e os capítulos na ordem `1, 1, 1.5, 2, 10`, seguidos dos bônus. Os dois capítulos `1` devem continuar distintos.
3. Selecione um capítulo individual e confirme a atualização da contagem. Depois selecione um intervalo invertendo os extremos; confirme que ambos os extremos e todos os capítulos intermediários ficam selecionados e que itens externos ao intervalo são desmarcados.
4. Consulte novamente e confirme que a seleção dos IDs ainda presentes foi mantida.
5. Com o catálogo visível, informe `https://example.test/manga` e tente atualizar. Confirme que a mensagem informa a fonte não suportada, o último catálogo continua visível e selecionável e o botão **Atualizar catálogo** permanece disponível para nova tentativa.
6. Informe `ftp://example.test/manga`; confirme a mensagem de endereço inválido e que o catálogo válido anterior continua visível.
7. Volte à **Biblioteca** e confirme a navegação. Essa tela ainda é um exemplo visual fixo; a consolidação dos catálogos persistidos faz parte da F008. A integração automatizada confirma que a consulta não substitui um registro local de outro provedor.

## Critérios que ainda precisam de validação manual

- No Windows 10/11, confirmar o layout da lista e dos controles, foco/teclado, nomes acessíveis e mensagens de catálogo anterior nos temas claro e escuro.
- Confirmar visualmente a ordem, a seleção por intervalo inclusivo e a preservação da seleção após nova consulta. A verificação do registro de outro provedor é automatizada porque a Biblioteca ainda não expõe catálogos persistidos.
- Confirmar que consulta/atualização da fixture e uma URL não registrada não abrem conexão de rede. Os testes automatizados instrumentam a fronteira de socket.
- A fixture termina rápido demais para validar manualmente a janela de cancelamento. O cancelamento com bloqueio entre consulta e commit é exercitado automaticamente; não o substitua por uma simulação na interface.

Essas conferências estão listadas no [checkpoint de implementação](../implementation-checkpoint.md) e não bloqueiam as próximas features.

## Validação automatizada

Testes focados de F004:

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_catalog_models.py tests/unit/domain/test_chapter_ordering.py tests/unit/application/test_get_catalog.py tests/unit/application/test_chapter_selection.py tests/integration/test_catalog_refresh.py tests/integration/test_catalog_fixture_flow.py tests/integration/test_provider_catalog_boundary.py tests/ui/test_add_manga_view.py tests/ui/test_chapter_selection_view.py tests/unit/infrastructure/providers/test_fixture_provider.py -q
```

Validação de regressão e análise estática:

```powershell
uv run --locked --python 3.12 pytest -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Falhas de consulta são verificadas com provedores/test doubles nos testes; a interface não oferece opções de resultado simulado.
