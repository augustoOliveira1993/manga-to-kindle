# Tarefas de Implementação: F008 — Biblioteca Local do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/library.md] e constituição.

## Dependências

- Features anteriores: F001–F007. Usar o único engine/runner Alembic de F001 e consolidar F005–F007 sem duplicar suas migrações ou repositórios de responsabilidade.
- F009–F011 dependem dos registros e consultas estáveis desta feature.

## Fase 1 — Setup

- [ ] T001 [P] Confirmar SQLAlchemy 2, Alembic e versões no lock existente; não substituir nem criar segundo engine.; arquivos/componentes: `pyproject.toml; uv.lock`
- [ ] T002 [P] Criar conjunto de dados de teste para manga, capítulos, jobs, páginas e exports em `tests/fixtures/library/`.

## Fase 2 — Foundational

- [ ] T003 Criar testes de integridade referencial e migrações sobre esquema criado por F001 em `tests/integration/test_library_schema.py`.
- [ ] T004 Implementar revisão Alembic de relações/índices da biblioteca e repositórios SQLAlchemy 2 em `src/manga_to_kindle/infrastructure/persistence/library/`.
- [ ] T005 Criar testes de mapeamento e invariantes do catálogo persistido em `tests/unit/infrastructure/test_library_mapping.py`.
- [ ] T006 Implementar camada de aplicação/repos reusáveis para Manga, Chapter, Page, DownloadJob e Export sem duplicar seus serviços originadores.; arquivos/componentes: `src/manga_to_kindle/infrastructure/persistence/library/; src/manga_to_kindle/application/library/`

## Fase 3 — Histórias de usuário

### US1 — Encontrar conteúdo na biblioteca local (P1)

**Objetivo**: Como pessoa usuária, quero pesquisar, filtrar e ordenar meus mangás e capítulos, para localizar rapidamente o conteúdo disponível no dispositivo.

**Teste independente**: Cadastrar fixtures de mangás/capítulos com metadados variados, favoritos e estados de arquivo; pesquisar termos com diferenças de caixa/acentos, aplicar filtros e conferir ordenação estável.

- [ ] T007 [US1] Criar testes de busca case/acento, filtros, favoritos e ordenação estável em `tests/integration/test_library_search.py`.
- [ ] T008 [US1] Implementar casos de uso de busca/filtro/favoritos/ordenação em `src/manga_to_kindle/application/library/queries.py`.
- [ ] T009 [US1] Criar testes de estados vazio, resultados, filtros e teclado em `tests/ui/test_library_view.py`.
- [ ] T010 [US1] Integrar listagem, pesquisa e filtros na tela Biblioteca usando consultas fora da UI thread.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/library_view.py`

### US2 — Consultar disponibilidade, downloads e histórico (P1)

**Objetivo**: Como pessoa usuária, quero ver quais capítulos já foram baixados, quais arquivos existem e como terminaram operações recentes, para saber o que está pronto sem repetir trabalho.

**Teste independente**: Criar trabalhos concluídos, parciais, cancelados e interrompidos, exports e arquivos faltantes; reiniciar o aplicativo e verificar classificações, progresso e histórico.

- [ ] T011 [US2] Criar testes de reconciliação de jobs interrompidos/terminados e caminhos ausentes em `tests/integration/test_library_availability.py`.
- [ ] T012 [US2] Implementar disponibilidade derivada de registros reais, paths e estado de F005/F006/F007; não marcar arquivo ausente como pronto.; arquivos/componentes: `src/manga_to_kindle/application/library/availability.py`
- [ ] T013 [US2] Criar testes de reinício, histórico de export/download e integridade de FK em `tests/integration/test_library_history.py`.
- [ ] T014 [US2] Integrar histórico e indicador de capítulo baixado/exportado à biblioteca e às telas correspondentes sem duplicar status.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/library_view.py; src/manga_to_kindle/presentation/qt/views/downloads_view.py`

### US3 — Remover com escopo explícito (P2)

**Objetivo**: Como pessoa usuária, quero escolher exatamente quais registros e arquivos excluir e revisar o impacto antes de confirmar, para evitar perder conteúdo por uma ação ambígua.

**Teste independente**: Preparar um mangá com capítulos, jobs, imagens e export; cancelar a confirmação e verificar que tudo permanece. Depois confirmar somente registros e, em outro caso, registros mais arquivos específicos; conferir escopo, hashes e recuperação de falha.

- [ ] T015 [US3] Criar testes de cancelamento da confirmação, exclusão de registro apenas, exclusão de paths selecionados e rollback/recuperação em `tests/security/test_library_delete_scope.py`.
- [ ] T016 [US3] Implementar plano de exclusão com prévia de escopo e confirmação explícita; verificar containment antes de remover arquivos em `src/manga_to_kindle/application/library/delete.py`.
- [ ] T017 [US3] Testar referências preservadas, arquivos compartilhados e recuperação de exclusão parcial em `tests/integration/test_library_delete_recovery.py`.
- [ ] T018 [US3] Integrar confirmação explícita à UI e manter ação cancelada sem alterações.; arquivos/componentes: `src/manga_to_kindle/presentation/qt/views/library_view.py`

## Fase 4 — Integração

- [ ] T019 Integrar modelos e registros produzidos por F005–F007 com consultas da biblioteca em `tests/integration/test_library_cross_feature.py`.
- [ ] T020 Testar cold start, migração, arquivo ausente e busca após reinício em `tests/integration/test_library_restart.py`.

## Fase 5 — Polish e validação

- [ ] T021 Documentar indexação, estados de disponibilidade e semântica exata das opções de exclusão no quickstart.; arquivos/componentes: `specs/008-local-library/quickstart.md`
- [ ] T022 Executar testes focados de migração, busca, integridade, recuperação e limites de exclusão; manter evidência no quickstart.; arquivos/componentes: `tests/integration/test_library_restart.py; specs/008-local-library/quickstart.md`

## Dependências e estratégia de execução

- Requer `F001:T017` a `F007:T024`; migrações novas são acrescentadas ao runner central. F009/F010/F011 aguardam `F008:T020`.
- Índices e repositórios precedem consultas; não reproduzir lógica dos módulos de downloads, imagens ou exports.
- MVP: US1 + US2; US3 só libera exclusão após aprovação de escopo na interface.

## Rastreabilidade

- RF-001–RF-012: T003–T010; RF-013–RF-023: T011–T014/T019–T020; RF-024–RF-033: T015–T022.
- RNF-001–RNF-008 e CS-001–CS-010: T003–T022, incluindo migração, reinício, arquivos externos ausentes e exclusão explícita.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001–F007. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
