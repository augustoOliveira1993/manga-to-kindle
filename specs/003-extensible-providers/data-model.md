# Modelo de Domínio — F003

| Tipo | Conteúdo | Invariantes |
|---|---|---|
| `NormalizedUrl` | scheme, IDNA host, effective port, path, query sem segredo | absoluta HTTP/S, sem userinfo, fragmento descartado, porta padrão canonicalizada. |
| `ProviderCapabilities` | operações, hosts/ports permitidos, rate limit, auth, permissão/evidência/revisão, atribuição/remoção | download false por default; só habilita com prova da capacidade exata. |
| `MangaProvider` | `supports`, `get_manga`, `get_chapters`, `get_pages` | supports puro; resposta validada antes de publicar. |
| `ProviderPageReference` | source ID estável, posição, referência de origem e destino validado | sem bytes/arquivo local. |
| `ProviderError` | código, retryable, safe-message key, contexto sanitizado | sem URL/query/token/body no log. |
| `ProviderRegistry` | lista explicitamente registrada | zero matches unsupported; múltiplos ambiguous. |

Futuro `ValidatedDestination` inclui hostname TLS, conjunto permitido e IP efetivo pinado; redirect retorna a validador antes de criar request. Fixture não instancia esses objetos de conexão.
