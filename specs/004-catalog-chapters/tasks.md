# Tarefas de Implementação: F004 — Catálogo e Capítulos do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/catalog.md](contracts/catalog.md) e constituição.

## Dependências

- Features anteriores: F001 (entidades/persistência), F002 (UI) e F003 (provider registry, fixture e URL policy).
- Reutilizar MangaProvider e erros tipados. Fonte remota real permanece bloqueada sem autorização; validar consulta com fixtures.

## Fase 1 — Setup

- [x] T001 [P] Preparar dependências de ordenação/normalização somente se já previstas no plano e lock; preservar IDs definidos pelos contratos.; arquivos/componentes: `pyproject.toml; uv.lock; src/manga_to_kindle/domain/chapter_ordering.py`
- [x] T002 [P] Criar fixtures de catálogos, capítulos especiais e decimais em `tests/fixtures/catalog/`.

## Fase 2 — Foundational

- [x] T003 Criar testes de normalização de metadados opcionais e IDs estáveis em `tests/unit/domain/test_catalog_models.py`.
- [x] T004 Implementar modelos/DTOs de catálogo que preservam ausência de dados e identidade estável em `src/manga_to_kindle/domain/catalog.py`.
- [x] T005 Criar testes do comparador numérico para inteiros, decimais, especiais e empates em `tests/unit/domain/test_chapter_ordering.py`.
- [x] T006 Implementar ordenação canônica e seleção inclusiva por intervalo em `src/manga_to_kindle/domain/chapter_ordering.py`.

## Fase 3 — Histórias de usuário

### US1 — Consultar e reconhecer catálogo (P1)

**Objetivo**: Como pessoa usuária, quero informar uma URL na área “Adicionar mangá” e ver o catálogo reconhecido, para confirmar que estou selecionando a obra correta antes de continuar.

**Teste independente**: Consultar a URL sintética documentada pelo provedor de fixtures e conferir os dados fictícios apresentados. Consultar uma URL sem provedor registrado e verificar que ela é recusada sem consulta à rede.

- [x] T007 [US1] Criar testes do caso de uso com fixture suportada/não suportada, metadados ausentes e falha tipada em `tests/unit/application/test_get_catalog.py`.
- [x] T008 [US1] Implementar caso de uso de consulta via registry F003 e mapear resposta para ViewModel em `src/manga_to_kindle/application/catalog/get_catalog.py`.
- [x] T009 [US1] Criar testes de estados de consulta na interface em `tests/ui/test_add_manga_view.py`.
- [x] T010 [US1] Integrar URL, resultado do catálogo e indicação de erro/carregamento à tela Adicionar mangá em `src/manga_to_kindle/presentation/qt/views/add_manga_view.py`, despachando em worker.

### US2 — Ordenar e selecionar capítulos (P1)

**Objetivo**: Como pessoa usuária, quero encontrar capítulos na ordem de leitura e selecionar um capítulo ou intervalo, para escolher com precisão o conteúdo que pretendo processar em uma feature posterior.

**Teste independente**: Usar uma fixture com capítulos numerados, decimais, especiais e números repetidos; comparar a ordem exibida com a regra canônica e conferir a seleção individual e inclusiva por intervalo.

- [x] T011 [US2] Criar testes da seleção individual, múltipla, intervalo e estabilidade após atualização em `tests/unit/application/test_chapter_selection.py`.
- [x] T012 [US2] Implementar estado de seleção por ID estável e ordenação determinística em `src/manga_to_kindle/application/catalog/chapter_selection.py`.
- [x] T013 [US2] Criar testes de widgets de seleção múltipla e intervalo em `tests/ui/test_chapter_selection_view.py`.
- [x] T014 [US2] Conectar lista de capítulos da UI ao estado de seleção sem usar posição visual como identidade.; arquivos/componentes: `src/manga_to_kindle/application/catalog/chapter_selection.py; src/manga_to_kindle/presentation/qt/views/add_manga_view.py`

### US3 — Atualizar catálogo e recuperar falha (P2)

**Objetivo**: Como pessoa usuária, quero atualizar os metadados e capítulos e manter o último catálogo válido se a atualização falhar, para não perder meu contexto durante uma indisponibilidade.

**Teste independente**: Consultar uma fixture, alterar os dados da fixture e atualizar; em seguida, injetar uma falha tipada de provedor e confirmar que a última versão válida permanece disponível, com indicação do erro e possibilidade de tentar novamente.

- [x] T015 [US3] Criar testes de refresh atômico, catálogo anterior preservado em falha e retry manual em `tests/integration/test_catalog_refresh.py`.
- [x] T016 [US3] Implementar refresh substituindo dados somente após resposta válida, mantendo versão anterior ao falhar, em `src/manga_to_kindle/application/catalog/refresh_catalog.py`.

## Fase 4 — Integração

- [x] T017 Integrar leitura/gravação do catálogo à persistência F001 com migração no runner único em `tests/integration/test_catalog_fixture_flow.py`, `tests/integration/test_catalog_refresh.py` e no repositório/migração únicos de F001.
- [x] T018 Validar consulta com provider fixture F003 e UI F002 sem rede externa em `tests/integration/test_catalog_fixture_flow.py`.

## Fase 5 — Polish e validação

- [x] T019 Documentar sintaxe de fixture, campos opcionais, ordem e seleção em `specs/004-catalog-chapters/quickstart.md` e README.
- [x] T020 Executar testes focados de ordenação, seleção e falha de refresh; registrar bloqueio de provider real sem autorização.; arquivos/componentes: `tests/integration/test_catalog_fixture_flow.py; specs/004-catalog-chapters/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017`, `F002:T015` e `F003:T015`. US1 precede US2 no fluxo de tela; o domínio de ordenação pode ser desenvolvido em paralelo com consulta.
- MVP: US1 + US2 com fixture, IDs estáveis e sem rede real.

## Rastreabilidade

- RF-001–RF-006: T003–T004/T007–T010; RF-007–RF-013: T005–T006/T011–T014; RF-014–RF-020: T015–T020.
- RNF-001–RNF-007 e CS-001–CS-007: T003–T020, incluindo determinismo, preservação de última resposta válida e responsividade.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001, F002 e F003. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
