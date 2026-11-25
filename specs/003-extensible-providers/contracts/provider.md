# Contrato `MangaProvider` — F003

```text
supports(url: NormalizedUrl) -> bool
get_manga(url: NormalizedUrl) -> Manga
get_chapters(manga: Manga) -> Sequence[Chapter]
get_pages(chapter: Chapter) -> Sequence[ProviderPageReference]
```

- `supports` é puro, sem DNS/rede/auth.
- `ProviderRegistry.resolve(url)` retorna exatamente um provider ou `UnsupportedSource`/`AmbiguousProvider`.
- Métodos potencialmente lentos serão chamados pelo caso de uso em worker. Validar ID, associação, conteúdo e ordem antes de persistir/publicar.
- Download capability exige evidência oficial para uso do conteúdo local, data de revisão, limite, atribuição e retirada; falta de prova fecha a capacidade.
- `FixtureProvider` atende só `fixture.invalid`, nunca acessa resolver/socket e marca toda resposta como simulada.
- Códigos mínimos: `InvalidUrl`, `UnsupportedScheme`, `UnsupportedSource`, `AmbiguousProvider`, `UnsafeDestination`, `RedirectRejected`, `CapabilityUnavailable`, `AccessRestricted`, `RateLimited`, `ContentUnavailable`, `ProviderUnavailable`, `ProviderResponseInvalid`.
- Mensagens PT-BR são resolvidas pela aplicação. Logs não incluem URL completa, query, credenciais, resposta ou conteúdo.
