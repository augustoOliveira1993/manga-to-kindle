# Contrato de Exportação — F007

- `PlanExport(selection, profile, options) -> ExportPlan` valida existência e perfil de todas as páginas antes de abrir output.
- O writer EPUB próprio usa `zipfile` e `xml.etree.ElementTree`; EbookLib não é dependência. A saída passou EPUBCheck 5.4.0.
- `KccCliWriter` verifica `--help` da CLI local em cada exportação, aceita somente versão 13.0.4 e cria MOBI nos perfis verificados K810/KPW34.
- `KccCliWriter.run(executable, argv, cwd, timeout, cancellation)` usa `shell=False`, argumentos presentes no help real, não baixa ferramenta, descarta stdout/stderr e não registra caminhos/metadata. A execução recebe cópias isoladas das páginas e publica somente MOBI com nome e assinatura esperados.
- `ValidateEpub(staged_path)` verifica container, metadata, cover, nav/TOC, spine order, resource closure, sem scripts/remote references; relatório só é sucesso sem erros de conformidade.
- `PublishExport` valida hash e não sobrescreve sem confirmação, então move atomicamente e grava estado completed.
- `SplitExport` só divide adapter capaz: capítulos quando possível, páginas em fronteira quando necessário, nunca dentro de página; fail se página excede tamanho máximo.
- Timeout é 15 min; cancel encerra o processo após até 3 s e força o término, limpa staging próprio e preserva originais/exports anteriores. MOBI exige idioma e não oferece divisão por tamanho.
