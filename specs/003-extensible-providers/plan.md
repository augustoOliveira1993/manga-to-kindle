# Plano de Implementação: F003 — Provedores Extensíveis

**Branch**: `003-extensible-providers` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo, bloqueio e conformidade

Definir contrato/registro tipados de `MangaProvider`, normalização segura, capabilities e erros; entregar somente provedor de fixtures offline. `B003-REAL-SOURCE` permanece aberto. Conforme constituição: sem conexão não autorizada, UI nunca executa DNS/rede; logs sanitizados; nenhum dado fictício passa por real.

## Contexto técnico e arquitetura

Python 3.12+ e camadas F001/F002. `domain.providers` declara `MangaProvider`, capabilities, page reference e erros sem dependência HTTP. `application.providers` normaliza URL pura, seleciona um provider e valida contratos. `infrastructure.providers.fixtures` atende sintético em memória. Não fazer discovery de plugins/entry points. HTTPX só é incluído quando fonte autorizada exigir tráfego; BeautifulSoup4 somente para parsing autorizado. Não são dependências para esta entrega.

`supports` é puro: esquema/host/port/path declarados, sem DNS. A seleção deve retornar um ou erro unsupported/ambiguous. Referência remota de página não vira `Page` local até F005 concluir download permitido. Capability declara operações, host CDN, auth, rate limits, autorização/evidência/revisão, atribuição e remoção; download fica desabilitado sem evidência específica.

## Validação futura de destino e erros

Qualquer network adapter futuro: validar HTTP/HTTPS antes de cada conexão; recusar userinfo e IP privado/loopback/link-local/multicast/reservado/cloud metadata; resolver A/AAAA, falhar em DNS misto e garantir endereço conectado igual ao validado; TLS valida hostname. Redirect manual, máximo 5 hops, revalidar esquema/host/IP/capability em cada salto, rejeitar downgrade/loop. HTTPX `follow_redirects=False`; sua API não resolve sozinha DNS rebinding. Fail closed se pinning não for comprovado.

Erros separados para URL inválida, scheme, fonte não suportada/ambígua, destino inseguro, redirect recusado, capability/auth, rate limit, conteúdo ausente, fonte indisponível e resposta inválida. Chamadas ficam em worker de aplicação quando operações externas eventualmente existirem.

## Contratos e estrutura

```text
domain/providers/{provider,capabilities,errors,page_reference}.py
application/providers/{normalize_url,registry,resolve_source,query_catalog}.py
infrastructure/providers/fixtures/{provider,data}.py
tests/{unit,integration,security}/providers/
```

Contrato detalhado em [contracts/provider.md](contracts/provider.md); tipos em [data-model.md](data-model.md). O cadastro é explícito, sem import side effects ou fallback host aproximado.

## Testes, rastreamento, riscos

Cobrir normalização/IDNA/portas/userinfo/fragment/query; registry 0/1/2; fixture sem DNS/socket; respostas estáveis; DNS fake IPv4/IPv6/misto/rebinding; redirects públicos/proibidos, 5/6 hops, downgrade/loop; erros tipados e redaction. Mapear RF-001–020, RNF-001–006 e CS-001–005. Falha de validação nunca chama conexão. Maior risco é validação prévia sem IP pinning efetivo; por isso não lançar real enquanto adapter não provar conexão ao destino validado.

F001/F002 precedem; F004/F005/F010 consomem a porta. Gate da fonte bloqueia só o adaptador remoto, não os contratos e fixtures. [research.md](research.md), [quickstart.md](quickstart.md).
