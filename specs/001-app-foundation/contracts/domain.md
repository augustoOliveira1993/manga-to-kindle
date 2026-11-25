# Contratos de Domínio — F001

Interfaces públicas tipadas em inglês, sem I/O nem side effects.

| Tipo | Invariantes |
|---|---|
| `Manga` | ID/título obrigatórios; metadados opcionais permanecem desconhecidos se ausentes. |
| `Chapter` | identidade estável e vínculo a Manga; título ou número de exibição; ordem não ambígua. |
| `Page` | ID, vínculo e posição únicos; `original_path` imutável por processadores. |
| `DownloadJob` | transições validadas; cancelamento; progresso não negativo/não excede total; terminal não volta a execução. |
| `DeviceProfile` | nome/valores validados; sem preset físico nesta feature. |
| `Export` | pedido de export com conteúdo/perfil/destino/estado; não declara arquivo pronto nem transferência. |

A aplicação consome tipos de domínio e DTOs; adapters usam repositórios/unit of work tipados. Testes substituem adapters por fakes. Domínio não importa QWidget, Session, HTTPX Response ou paths de instalação.
