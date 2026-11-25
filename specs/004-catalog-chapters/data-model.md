# Modelo de Dados — F004

| Registro | Dados | Regras |
|---|---|---|
| `CatalogSnapshot` | Manga + lista completa de Chapter + provider/source + atualização | substituição atômica; não é parcial; fonte de fixtures carrega marker demo. |
| `CatalogMetadata` | title, author?, cover local?, language? | title obrigatório; opcionais ausentes continuam null/ausentes. |
| `ChapterCatalogEntry` | stable source-qualified ID, display title/number, volume?, availability?, source order? | duplicidade de ID em um mangá rejeita snapshot; título/número só pode faltar se outro identifica para exibição. |
| `ChapterOrderKey` | kind numeric/special, numeric value?, source sequence?, stable ID | número explícito decimal primeiro; special depois; empate determinístico. |
| `ChapterSelection` | ordered set de IDs selecionados | intervalo inclusivo na lista canônica; refresh conserva somente IDs presentes. |
| `CatalogRefreshResult` | success/failure/cancelled, snapshot version/error code | apenas success completo substitui snapshot persistido. |

Imagem de capa remota não faz parte do modelo de renderização nesta feature; somente asset local fixture ou placeholder. Persistência física será migrada por F008, usando repositório F001.
