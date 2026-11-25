# Contratos de Catálogo — F004

- `QueryCatalog(url) -> CatalogSnapshot` usa `ProviderRegistry` e `MangaProvider` de F003, executado em worker.
- `RefreshCatalog(manga_id) -> RefreshResult` só commita snapshot validado e completo; em erro/cancelamento mantém versão anterior.
- `OrderChapters(chapters) -> Sequence[ChapterId]` não muta IDs nem interpreta número no título; aplica número explícito, source order, stable ID.
- `SelectChapter(id)` e `SelectRange(first_id, last_id)` atuam sobre ordem atual e resultam em conjunto de IDs; seleção não depende de índice persistido.
- `CatalogView` traduz opcionais ausentes em omitido/“Não informado”; capa apenas fixture local; banner de simulação sempre visível.
- Mensagens não incluem URL completa/query. Nenhum método de F004 realiza request fora de fixture offline.
