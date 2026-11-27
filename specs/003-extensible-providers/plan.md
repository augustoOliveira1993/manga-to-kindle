# Plano de Implementação: F003 — Provedores Extensíveis

**Branch**: `003-extensible-providers` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo, bloqueio e conformidade

Definir contrato/registro tipados de `MangaProvider`, normalização segura, capabilities e erros; manter a fixture offline e integrar NDL apenas para consulta pontual de item individual PDM. O usuário autorizou esse escopo em 2026-11-27. Metadados são limitados localmente a uma consulta por minuto e imagens a 12 requests por minuto; isso não é cota declarada pela NDL. Atualizações periódicas e outros provedores continuam bloqueados. Conforme constituição: UI nunca executa DNS/rede; logs sanitizados; nenhum dado fictício passa por real.

## Contexto técnico e arquitetura

Python 3.12+ e camadas F001/F002. `domain.providers` declara `MangaProvider`, capabilities, page reference e erros sem dependência HTTP. `application.providers` normaliza URL pura, seleciona um provider e valida contratos. `infrastructure.providers` contém fixture sintética e integração NDL. O transporte de rede usa a biblioteca padrão, conecta diretamente somente a IPs previamente validados, preserva verificação TLS/SNI, não usa proxy ambiental e revalida cada salto de redirect pela política central. Não fazer discovery de plugins/entry points nem scraping HTML.

`supports` é puro: esquema/host/porta/caminho declarados, sem DNS. A seleção deve retornar um provedor ou erro unsupported/ambiguous. NDL aceita somente URL de item `/dl/book/<PID>`, consulta um único objeto de metadados por ação e só emite referências IIIF do registro validado. A permissão local se limita a item individual PDM selecionado pelo usuário. O catálogo não oferece atualização periódica. Referência remota só vira `Page` local após F005 baixar, validar e gravar atomicamente os bytes.

## Validação futura de destino e erros

Cada request valida HTTPS, host exato e porta; recusa IP privado/loopback/link-local/multicast/reservado/cloud metadata e DNS misto; conecta diretamente a um endereço público aprovado e confere o peer conectado; TLS valida o hostname. Redirects são seguidos somente após revalidar cada salto, com limite de cinco, detecção de loops e bloqueio de downgrade. Para NDL, a allowlist inclui somente o host IIIF e o bucket de entrega S3 exato observado na resposta do endpoint oficial. Outros hosts continuam recusados.

Erros separados para URL inválida, scheme, fonte não suportada/ambígua, destino inseguro, redirect recusado, capability/auth, rate limit, conteúdo ausente, fonte indisponível e resposta inválida. Chamadas ficam em worker de aplicação quando operações externas eventualmente existirem.

## Contratos e estrutura

```text
domain/providers/{provider,capabilities,errors,page_reference}.py
application/providers/{normalize_url,registry,resolve_source,query_catalog}.py
infrastructure/providers/fixtures/{provider,data}.py
infrastructure/providers/ndl_provider.py
infrastructure/network/pinned_http_transport.py
tests/{unit,integration,security}/providers/
```

Contrato detalhado em [contracts/provider.md](contracts/provider.md); tipos em [data-model.md](data-model.md). O cadastro é explícito, sem import side effects ou fallback host aproximado.

## Testes, rastreamento, riscos

Cobrir normalização/IDNA/portas/userinfo/query; registry 0/1/2; fixture sem DNS/socket; metadados e IDs NDL estáveis; limite local; destino validado, IP conectado e SNI; redirect para host exato aprovado; redirect não aprovado, loop, downgrade e excesso de saltos recusados; resposta inválida e redaction. Os testes de rede ficam isolados e não consultam NDL. A consulta pontual e o download individual autorizado podem ser exercitados separadamente; resultados ficam no quickstart/checkpoint.

F001/F002 precedem; F004 usa os metadados e F005 consome as referências. F010 não pode usar NDL para periodicidade. [research.md](research.md), [quickstart.md](quickstart.md).
