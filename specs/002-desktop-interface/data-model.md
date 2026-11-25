# Modelo de Apresentação — F002

F002 não acrescenta schema persistido. View states:

| Tipo | Campos | Regras |
|---|---|---|
| `PageLoadState` | fase empty/loading/success/error/cancelled, mensagem/ação | transições do resultado do caso de uso. |
| `DemoMarker` | label, fixture ID, `simulated` | visível em catálogo/download/conversão demo. |
| `ChapterSelection` | conjunto de `ChapterId` | identidade, não índice. |
| `ConversionDraft` | IDs, pasta, perfil demo, formato demo | valida campos; não grava nem marca Export pronto. |
| `ThemePreference` | light/dark | default light; persiste em config F001. |
| `OperationProgress` | operation ID, etapa, concluído/total?, estado | progresso não negativo e cancelamento idempotente. |

URL fica em memória de formulário e é descartada ao limpar/fechar; não aparece em log/mensagem completa.
