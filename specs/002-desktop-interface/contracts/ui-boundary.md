# Contrato da Fronteira UI — F002

- Qt envia comandos de aplicação tipados (`LoadLibrary`, `ValidateUrl`, `StartDemoOperation`, `CancelOperation`, `SaveTheme`) e recebe snapshot, progress, success, erro tipado ou cancelled.
- Worker sinaliza `started(operation_id)`, `progress(operation_id, completed, total?)`, `succeeded`, `failed(error_code)` e `cancelled`; apresentação só atualiza Widgets na thread principal.
- Todo dado sintético expõe `simulated=true`/rótulo PT-BR; UI não acessa DB, HTTP client ou arquivos de conteúdo diretamente.
- Cancelamento é idempotente; o lifecycle de F001 coordena worker ativo ao fechar.
- Foco/atalhos são explícitos: setas/Espaço para lista, foco visível, labels acessíveis, estados não dependentes só de cor.
