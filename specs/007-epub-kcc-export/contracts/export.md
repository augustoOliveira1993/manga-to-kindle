# Contrato de Exportação — F007

- `PlanExport(selection, profile, options) -> ExportPlan` valida existência e perfil de todas as páginas antes de abrir output.
- `ExportAdapter.capabilities(version/evidence) -> Capabilities` declara somente formatos/opções comprovados; ausência fecha opção específica.
- `NativeEpubAdapter` permanece gated por EbookLib license/fixed-layout; a interface interna recebe metadata/ordered processed pages e devolve staged package. Se gate não passar, não oferece essa saída.
- `KccAdapter.run(executable, argv, cwd, timeout, cancellation)` usa `shell=False`, seleciona apenas args confirmados da versão, não baixa ferramenta, coleta output sanitizado; rede de version check só com consentimento explícito por execução ou offline confirmado.
- `ValidateEpub(staged_path)` verifica container, metadata, cover, nav/TOC, spine order, resource closure, sem scripts/remote references; relatório só é sucesso sem erros de conformidade.
- `PublishExport` valida hash e não sobrescreve sem confirmação, então move atomicamente e grava estado completed.
- `SplitExport` só divide adapter capaz: capítulos quando possível, páginas em fronteira quando necessário, nunca dentro de página; fail se página excede tamanho máximo.
- Cancel encerra subprocesso ≤5 s (força se necessário), limpa staging próprio e deixa originais/exports anteriores intactos.
