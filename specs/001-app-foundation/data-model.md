# Modelo de Dados — F001

Tipos e invariantes ficam em `domain`; mapeamento ORM em `infrastructure.persistence`, nunca vazando para a UI.

| Entidade | Campos/invariantes mínimos |
|---|---|
| Manga | `id` estável; `title` obrigatório; origem opcional; capítulos ordenáveis. |
| Chapter | `id`, `manga_id`, título e/ou número de exibição, ordem de leitura não ambígua e única no mangá. |
| Page | `id`, `chapter_id`, `position` única; referência local à imagem original; não pode sobrescrever original. |
| DownloadJob | `id`, alvo, estado, timestamps, progresso/total opcionais e pedido de cancelamento; estado terminal não retorna à execução; progresso ∈ [0,total conhecido]. F001 não inicia download. |
| DeviceProfile | `id`, nome, preferências tipadas e validadas; não presume modelo/dimensões. |
| Export | `id`, referências de conteúdo, snapshot de perfil, destino local e estado; representa pedido, não arquivo pronto ou envio. |

IDs não são índice nem título. Desconhecido é `None`, nunca zero inventado. Timestamps são UTC timezone-aware. Caminhos são relativos à raiz gerenciada quando viável.

## Persistência

Revisão inicial Alembic `0001_initial_schema`, tabela de versão e constraints de FK/uniqueness. Features persistentes posteriores acrescentam suas revisões sem redefinir semântica desses contratos; F008 consolida relações e consultas sobre entidades adicionadas em F001–F007. F001 não guarda conteúdo binário, página remota como arquivo local ou senha.

Relações iniciais: `Manga 1—N Chapter 1—N Page`; `DownloadJob` referencia o alvo persistido; `Export N—N Chapter` via associação ordenada e snapshot imutável de DeviceProfile. O schema físico será consolidado em F008.
