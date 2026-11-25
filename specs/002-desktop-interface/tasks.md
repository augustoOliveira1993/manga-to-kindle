# Tarefas de Implementação: F002 — Interface Desktop do Manga to Kindle

**Fonte da verdade**: [spec.md](spec.md), [plan.md](plan.md), [contracts/ui-boundary.md](contracts/ui-boundary.md) e constituição.

## Dependências

- Feature anterior: F001 (composição, logging, contratos e ciclo de vida).
- Componentes compartilhados: casca PySide6 e adaptador de workers/sinais; nenhuma operação bloqueante na thread gráfica.
- Dados de demonstração devem ser identificados como simulados; F003/F004/F005 conectam serviços reais apenas se autorizados.

## Fase 1 — Setup

- [x] T001 [P] Preparar dependência e configuração PySide6 já previstas em `pyproject.toml` e no lock, sem adicionar toolkit paralelo.
- [x] T002 [P] Criar harness Qt para testes de widgets em `tests/ui/` com fixtures de aplicação.

## Fase 2 — Foundational

- [x] T003 Criar testes de navegação, tema e emissão de ações em `tests/ui/test_main_window.py`.
- [x] T004 Implementar janela principal, navegação Biblioteca/Adicionar mangá/Downloads/Conversão/Configurações e roteamento de páginas em `src/manga_to_kindle/presentation/qt/`.
- [x] T005 Criar testes do boundary de UI e de despacho de operações longas em `tests/unit/presentation/test_worker_adapter.py`.
- [x] T006 Implementar adaptador de operações em workers, sinais tipados para progresso/resultado/erro e cancelamento em `src/manga_to_kindle/presentation/qt/workers/`; nenhum I/O bloqueante no GUI thread.

## Fase 3 — Histórias de usuário

### US1 — Navegar pela biblioteca e pelas áreas (P1)

**Objetivo**: Como pessoa usuária, quero encontrar as áreas principais do aplicativo e entender quando a biblioteca está vazia para saber como começar.

**Teste independente**: Abrir cada área da navegação e confirmar que o conteúdo, o foco do teclado e o estado correspondente aparecem sem conexão externa.

- [x] T007 [US1] Criar teste de teclado, foco e navegação entre as cinco áreas em `tests/ui/test_navigation_accessibility.py`.
- [x] T008 [US1] Implementar estados vazios e rotas de cada área em `src/manga_to_kindle/presentation/qt/views/`, mantendo rótulos em português brasileiro.

### US2 — Adicionar demonstração e escolher capítulos (P1)

**Objetivo**: Como pessoa usuária, quero informar uma URL e selecionar vários capítulos para entender o fluxo de entrada antes da conexão com serviços reais.

**Teste independente**: Informar uma URL sintaticamente válida, acompanhar o estado de carregamento simulado e selecionar e desmarcar capítulos com teclado e mouse.

- [x] T009 [US2] Criar testes de URL, seleção múltipla e identificação explícita de catálogo simulado em `tests/ui/test_add_manga_view.py`.
- [x] T010 [US2] Implementar campo URL, lista selecionável e estado de demonstração em `presentation/qt/views/add_manga_view.py`, com contratos de apresentação sem acessar rede.

### US3 — Acompanhar downloads e conversões simulados (P1)

**Objetivo**: Como pessoa usuária, quero acompanhar progresso, sucesso, falha ou cancelamento para entender como serão apresentados os trabalhos futuros.

**Teste independente**: Iniciar uma operação de demonstração, observar progresso, navegar para outra área e cancelar a operação sem bloquear a janela.

- [x] T011 [US3] Criar testes de estados carregando/progresso/erro/sucesso e cancelamento visual em `tests/ui/test_jobs_views.py`.
- [x] T012 [US3] Implementar visualizações de Downloads e Conversão usando fixtures claramente rotuladas em `presentation/qt/views/`; conectar apenas aos sinais do worker boundary.

### US4 — Personalizar aparência e operar sem mouse (P2)

**Objetivo**: Como pessoa usuária, quero escolher tema claro ou escuro e usar as funções principais com teclado para adaptar a interface às minhas preferências.

**Teste independente**: Alternar tema, reiniciar a aplicação e completar navegação, seleção de capítulos e conversão simulada usando somente teclado.

- [x] T013 [US4] Criar testes de alternância claro/escuro, atalhos, navegação por Tab e foco visível em `tests/ui/test_theme_keyboard.py`.
- [x] T014 [US4] Implementar tema claro/escuro, atalhos e ordem de foco acessível em `presentation/qt/theme.py` e `presentation/qt/shortcuts.py`.

## Fase 4 — Integração

- [x] T015 Testar composição da janela com bootstrap e ciclo de vida F001 em `tests/integration/test_desktop_startup.py`.
- [x] T016 Verificar que operações simuladas não bloqueiam a thread gráfica nem emitem progresso após cancelamento em `tests/integration/test_ui_responsiveness.py`.

## Fase 5 — Polish e validação

- [x] T017 Documentar execução, controles de teclado, temas e aviso de dados simulados no `README.md` e `specs/002-desktop-interface/quickstart.md`.
- [x] T018 Executar testes focados da UI em modo headless quando suportado pela configuração e registrar limitações no quickstart.; arquivos/componentes: `tests/ui/test_jobs_views.py; specs/002-desktop-interface/quickstart.md`

## Dependências e estratégia de execução

- F001:T017 é pré-requisito; T004/T006 são fundacionais. Para cada US, executar seu teste antes do widget correspondente.
- T001–T002 são paralelizáveis; manter integração real fora desta feature.
- MVP: US1 e US2, navegáveis com fixtures explicitamente simuladas.

## Rastreabilidade

- RF-001–RF-004: T003–T008; RF-005–RF-008: T009–T010; RF-009–RF-012: T011–T012; RF-013–RF-016: T013–T018.
- RNF-001–RNF-006 e CS-001–CS-007: T005–T018, com foco em responsividade, acessibilidade, idioma, confiabilidade e identificação das simulações.

## Dependências explícitas por ID

- T001 e T002 são raízes paralelizáveis após as dependências de feature: F001. Em F001, essas raízes não têm dependência externa.
- T003 depende de T001 e T002. Cada tarefa T004 em diante depende da tarefa imediatamente anterior no mesmo tasks.md; essa ordem conservadora preserva os gates, os testes antes da implementação e as integrações indicadas acima.
- No MCP, cada dependência aponta para o ID da tarefa equivalente; tarefas-raiz também dependem da última tarefa de integração das features predecessoras listadas.
- Nenhuma tarefa aparece concluída nesta etapa.
