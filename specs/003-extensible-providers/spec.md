# Especificação de Funcionalidade: F003 — Provedores Extensíveis do Manga to Kindle

**Branch da funcionalidade**: `003-extensible-providers`

**Criada em**: 2026-11-25

**Status**: Aprovado para provedor NDL pontual e limitado; outros provedores seguem bloqueados

**Entrada**: Definir o contrato `MangaProvider` com `supports`, `get_manga`,
`get_chapters` e `get_pages`; registro de provedores, normalização de URLs, erros tipados
e capacidades declaradas. Aceitar somente HTTP/HTTPS, validar destinos e bloquear acesso
a redes privadas. Incluir provedor de fixtures e um provedor NDL limitado a consultas
pontuais de metadados e download local explícito de itens individuais PDM. Atualizações
periódicas e outros provedores permanecem bloqueados.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Usar o provedor de demonstração sem acesso remoto (Prioridade: P1)

Como pessoa usuária, quero informar uma URL reconhecida pelo provedor de demonstração e
ver mangá, capítulos e páginas fictícios claramente identificados, sem confundi-los com
conteúdo real.

**Por que esta prioridade**: Permite validar o contrato e a seleção de provedores sem
realizar downloads ou depender de uma fonte externa ainda não aprovada.

**Teste independente**: Consultar uma URL sintética de fixture e verificar resultados
determinísticos em `get_manga`, `get_chapters` e `get_pages`, sem resolução DNS ou rede.

**Cenários de aceitação**:

1. **Dado** uma URL sintética atendida pelo provedor de fixtures, **quando** o registro
   seleciona o provedor, **então** os três métodos retornam dados de demonstração
   identificados como fictícios, com capítulos e referências de página em ordem estável.
2. **Dado** a mesma fixture consultada mais de uma vez, **quando** o conteúdo é solicitado,
   **então** o resultado é determinístico e nenhum dado fictício é apresentado como fonte
   ou download real.

### História 2 — Rejeitar URLs inválidas, fontes não suportadas e destinos inseguros
(Prioridade: P1)

Como pessoa usuária, quero receber um erro compreensível quando uma URL não for aceita para
evitar consultas a serviços errados ou a redes privadas.

**Por que esta prioridade**: Uma URL fornecida por usuário pode direcionar a aplicação a
um serviço interno ou expor conteúdo e credenciais.

**Teste independente**: Passar URLs malformadas, esquemas proibidos, fontes sem provedor,
endereços privados e redirecionamentos inseguros; verificar erro tipado e nenhuma conexão
ao destino rejeitado.

**Cenários de aceitação**:

1. **Dado** uma URL inválida ou fora de HTTP/HTTPS, **quando** a pessoa usuária tenta
   consultá-la, **então** a validação falha antes de qualquer resolução de destino ou
   chamada de rede e exibe uma mensagem acionável em português.
2. **Dado** uma URL válida cujo domínio não é atendido por um provedor registrado,
   **quando** a seleção é solicitada, **então** o resultado é um erro `UnsupportedSource`
   sem tentar descobrir ou acessar o site.
3. **Dado** um domínio que resolve para endereço privado, local, link-local ou não
   globalmente roteável, **quando** uma chamada externa é simulada, **então** o destino é
   rejeitado antes da conexão.
4. **Dado** um redirecionamento para esquema proibido, endereço não público, destino não
   declarado pelo provedor ou cadeia circular, **quando** a resposta é processada,
   **então** o redirecionamento é bloqueado e reportado como erro tipado.

### História 3 — Adicionar provedores com capacidades e autorização verificáveis
(Prioridade: P2)

Como pessoa mantenedora, quero registrar provedores com operações, domínios, limites e
evidências declarados para ampliar as fontes sem duplicar regras de segurança ou presumir
permissões de download.

**Por que esta prioridade**: Extensibilidade segura exige que cada fonte exponha seus
limites e sua autorização antes de ser usada.

**Teste independente**: Registrar um provedor de teste com capacidades explícitas e
verificar seleção única, ausência de seleção, seleção ambígua e bloqueio de capacidade
sem evidência autorizada.

**Cenários de aceitação**:

1. **Dado** um registro com exatamente um provedor que declara suporte à URL normalizada,
   **quando** o registro seleciona a fonte, **então** todos os métodos são encaminhados a
   esse provedor.
2. **Dado** mais de um provedor compatível com a mesma URL, **quando** a seleção ocorre,
   **então** o registro retorna `AmbiguousProvider` em vez de escolher silenciosamente.
3. **Dado** um provedor sem evidência verificável de autorização para download,
   **quando** declara capacidade de baixar páginas, **então** essa capacidade não fica
   disponível e a integração real permanece bloqueada.

### Casos extremos

- URL vazia, com espaços, esquema relativo, esquema `file`, `ftp`, `data` ou `gopher`.
- URL com credenciais embutidas, porta inválida, porta não declarada ou sintaxe IPv6
  ambígua.
- Nome de domínio internacionalizado, ponto final, representação alternativa de IP ou
  endereço IPv4 encapsulado em IPv6.
- DNS com resposta privada, local, link-local, reservada, multicast, não especificada,
  metadados de nuvem ou conjunto misto de endereços públicos e não públicos.
- Resolução DNS muda entre validação e conexão, ou o endereço efetivamente conectado não
  corresponde ao endereço público validado.
- Redirecionamento relativo, cadeia acima do limite, loop, troca para HTTP após HTTPS,
  destino fora dos domínios declarados ou host que passa por sufixo enganoso.
- Nenhum provedor registrado suporta a URL ou vários provedores reivindicam suporte.
- Provedor declara metadados, capítulos ou páginas, mas não implementa uma dessas
  capacidades.
- Fonte retorna resposta inválida, itens repetidos, capítulos sem ordenação estável ou
  referências de página fora de HTTP/HTTPS.
- Fonte exige autenticação, CAPTCHA, pagamento, remove conteúdo, retorna bloqueio de
  acesso ou indica limite de requisições.
- Evidência de licença/termos expira, muda, deixa de estar disponível ou não cobre páginas
  e exportação local.
- URL ou resposta contém token, cookie, credencial ou dado sensível que não deve aparecer
  nos logs.
- O provedor de fixtures recebe uma URL qualquer que não pertença ao seu identificador
  sintético; ele não deve tentar resolver ou acessar esse endereço.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A aplicação deve definir o contrato `MangaProvider` com as operações
  `supports(url)`, `get_manga(url)`, `get_chapters(manga)` e `get_pages(chapter)`.
- **RF-002**: `supports` deve receber uma URL já normalizada, retornar somente se o
  provedor reivindica aquela fonte e não realizar DNS, rede, autenticação ou leitura de
  conteúdo.
- **RF-003**: `get_manga` deve retornar um Manga com identidade estável e metadados
  fornecidos pela fonte; `get_chapters` deve retornar capítulos com identidade e ordem
  estáveis; `get_pages` deve retornar referências de página estáveis e ordenadas.
- **RF-004**: As referências de `get_pages` devem preservar a referência da fonte e o
  destino remoto validado, sem gravar bytes de imagem, sobrescrever imagem original ou
  fingir que uma página remota já é um `Page` local de F001. A persistência local de uma
  página cabe ao fluxo posterior de download autorizado.
- **RF-005**: O registro deve permitir inscrição explícita de provedores internos do
  produto. A seleção deve normalizar a URL e retornar exatamente um provedor compatível;
  nenhuma correspondência deve gerar `UnsupportedSource` e mais de uma deve gerar
  `AmbiguousProvider`.
- **RF-006**: `supports` deve fazer correspondência por esquema, host normalizado e regras
  de caminho declaradas pelo provedor. Correspondência por substring ou sufixo de host não
  declarado não é válida.
- **RF-007**: A normalização deve remover espaços externos, aceitar apenas URLs absolutas
  HTTP ou HTTPS, canonicalizar esquema e host, aplicar representação consistente a nomes
  internacionalizados, remover porta padrão e fragmento e preservar a semântica de
  caminho e consulta. Credenciais embutidas devem ser rejeitadas.
- **RF-008**: A normalização e a seleção de provedor devem ser determinísticas e não podem
  fazer chamadas de rede. Portas não padrão só podem ser aceitas quando declaradas pelo
  provedor selecionado.
- **RF-009**: Destinos externos devem ser validados antes de cada conexão. Endereços
  privados, loopback, link-local, não especificados, multicast, reservados, metadados de
  nuvem ou outros endereços não globalmente roteáveis devem ser bloqueados em IPv4 e IPv6.
  Respostas DNS mistas, com qualquer destino proibido, devem falhar fechadas.
- **RF-010**: A validação deve cobrir o endereço efetivamente conectado para impedir que
  uma mudança de DNS entre validação e conexão direcione a operação para endereço proibido.
- **RF-011**: Redirecionamentos não devem ser seguidos automaticamente antes da validação.
  Cada destino deve ser normalizado e validado com as mesmas regras de esquema, host,
  DNS, endereço e capacidade declarada. HTTPS para HTTP, loop e mais de cinco saltos devem
  ser rejeitados.
- **RF-012**: Um provedor pode declarar os domínios adicionais necessários para CDN ou
  redirecionamento; destinos não declarados devem ser recusados mesmo quando públicos.
- **RF-013**: Cada provedor deve declarar capacidades de metadados, listagem de capítulos,
  referências de páginas, autenticação, downloads autorizados, limites de requisições,
  atribuição exigida e política de remoção de conteúdo. Uma declaração de download deve
  apontar para evidência oficial que cubra especificamente o conteúdo e o uso local.
- **RF-014**: Se uma fonte exigir autenticação, CAPTCHA, DRM, pagamento ou outra restrição,
  o provedor deve retornar erro tipado e encerrar o fluxo sem contornar a restrição.
- **RF-015**: Erros devem ser tipados pelo menos para URL inválida/esquema não suportado,
  fonte não suportada, seleção ambígua, destino inseguro, redirecionamento recusado,
  capacidade indisponível, acesso requerido/restrito, limite excedido, conteúdo ausente,
  indisponibilidade da fonte e resposta inválida do provedor.
- **RF-016**: A aplicação deve incluir um provedor de fixtures com dados determinísticos
  e explicitamente fictícios. Ele deve suportar somente seu identificador sintético,
  retornar Manga, Chapter e referências de página sem DNS, rede ou acesso a fontes reais.
- **RF-017**: Provedores reais exigem autorização específica, documentação oficial dos
  endpoints, escopo de uso, limites locais, atribuição/remoção e destinos aprovados. A NDL
  só pode consultar um item identificado pelo usuário e baixar localmente um item
  individual confirmado como parte do corpus PDM da Next Digital Library.
- **RF-018**: O provedor NDL não pode fazer atualização periódica, descoberta ampla,
  distribuição ou acesso contínuo. Nenhum provedor pode simular sucesso real, apresentar
  fixture sob identidade de outra fonte ou afirmar que uma operação não executada funciona.
- **RF-019**: URL completa, parâmetros, credenciais e resposta de conteúdo não devem ser
  registrados nos logs. Erros visíveis à pessoa usuária devem ser em português e sem
  ecoar dados sensíveis.
- **RF-020**: Testes devem cobrir seleção do provedor de fixtures, URL inválida, fonte não
  suportada, seleção ambígua, capacidades, endereços privados e validação de cada salto
  de redirecionamento. Os testes de rede devem usar DNS/transporte simulados e não fazer
  chamadas reais.

### Requisitos Não Funcionais

- **RNF-001**: Identificadores, contratos e erros devem estar em inglês; interface e
  documentação voltadas à pessoa usuária devem estar em português brasileiro.
- **RNF-002**: Nenhuma validação, DNS, leitura de rede ou processamento potencialmente
  bloqueante pode bloquear a thread gráfica.
- **RNF-003**: Todas as verificações de URL e destino devem falhar de forma segura:
  entrada inválida, resposta ambígua ou falha de verificação nunca pode resultar em
  conexão permissiva.
- **RNF-004**: Logs devem omitir segredos, credenciais, tokens, conteúdo de livros e URL
  completa quando houver parâmetros sensíveis.
- **RNF-005**: Respeitar limites de origem publicados. Se uma fonte não publicar limite
  numérico, qualquer uso autorizado precisa de limite local conservador claramente
  identificado como política do aplicativo; isso não autoriza uso contínuo ou periódico.
- **RNF-006**: O provedor de fixtures deve executar sem internet e produzir os mesmos
  resultados para as mesmas entradas.

### Entidades Principais

- **`MangaProvider`**: Contrato de consulta da fonte com `supports`, `get_manga`,
  `get_chapters` e `get_pages`.
- **Registro de provedores**: Conjunto explícito de provedores disponíveis, responsável
  por seleção única, erro de ausência e erro de ambiguidade.
- **Capacidades do provedor**: Operações suportadas, domínios/portas permitidos,
  necessidade de autenticação, permissão de download com evidência, limites, atribuição e
  obrigações de remoção.
- **Referência de página do provedor**: Identidade e posição de uma página, com referência
  da fonte e destino remoto; não representa bytes baixados nem um arquivo `Page` local.
- **`ProviderError`**: Categoria tipada que permite tratar erro de URL, seleção,
  segurança, permissão, limite e resposta sem interpretar texto arbitrário.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: 100% das variantes de URL definidas nos testes normalizam de forma
  determinística; variantes equivalentes selecionam o mesmo provedor.
- **CS-002**: A fixture é selecionada para seu identificador sintético e seus métodos
  retornam manga, capítulos e referências de página na ordem especificada, com zero
  chamadas DNS ou de rede.
- **CS-003**: 100% dos casos inválidos de esquema, sintaxe, endereço privado, DNS misto,
  destino de redirecionamento proibido, loop e excesso de saltos são rejeitados antes de
  qualquer conexão ao destino bloqueado.
- **CS-004**: URL inválida, fonte sem suporte e fonte com múltiplos provedores compatíveis
  resultam, respectivamente, em erros tipados distintos e mensagens acionáveis em
  português.
- **CS-005**: Todos os testes de seleção, erros, capacidades, segurança de destino e
  redirecionamento passam sem usar rede real.
- **CS-006**: Nenhum provedor é marcado como autorizado a baixar sem referência verificável
  que cubra a fonte, o conteúdo e o uso pretendido.
- **CS-007**: F003 entrega a fixture offline e consulta NDL somente para URL de item
  individual autorizada; nenhum refresh periódico é registrado ou iniciado.

## Premissas

- F003 depende dos contratos locais de F001 (`Manga`, `Chapter`, `Page` e `DownloadJob`)
  e pode ser integrado ao campo de URL de F002 quando essa interface estiver implementada.
- F001 define `Page` como referência a imagem local. Por isso, `get_pages` retorna
  referências remotas separadas; converter uma referência em arquivo `Page` local pertence
  a um fluxo posterior de download autorizado.
- O registro nesta feature inclui provedores internos explicitamente cadastrados; não
  carrega código de plugins de terceiros nem oferece marketplace.
- O provedor de fixtures usa URL sintética não resolvível, como
  `https://fixture.invalid/manga/demo`, que é tratada localmente e nunca enviada à rede.
- O limite padrão de redirecionamentos é cinco; a pessoa mantenedora pode alterar esse
  limite somente com justificativa de segurança e testes equivalentes.
- O projeto não tem `docs/roadmap.md`; o checkout contém specs F001 e F002 e nenhuma
  implementação de provedor ou fonte externa. Não há predecessores anteriores adicionais.
- A revisão da autorização NDL e do escopo humano ocorreu em 2026-11-27. Mudanças de
  termos ou permissões devem ser verificadas antes de ampliar o escopo.

## Dependências, Bloqueios, Riscos e Limites de Escopo

### Dependências

- A constituição em [`../../.specify/memory/constitution.md`](../../.specify/memory/constitution.md)
  determina acesso autorizado, respeito a limites e licenças, privacidade, idioma e
  comportamento sem contorno de restrições.
- F001 — [Fundação do Manga to Kindle](../001-app-foundation/spec.md) fornece os contratos
  de domínio e persistência local.
- F002 — [Interface Desktop do Manga to Kindle](../002-desktop-interface/spec.md) define
  o campo URL, estados de tela e mensagens do fluxo de entrada; em F002 os dados permanecem
  simulados.
- A API MangaDex não está aprovada. A documentação consultada declara uso
  público e gratuito sob condições de crédito a MangaDex e grupos, remoção de conteúdo e
  ausência de anúncios/serviços pagos, mas não declara autorização específica para baixar
  imagens de capítulos e exportá-las localmente para Kindle. A conclusão de que isso é
  insuficiente para habilitar um provedor real é uma inferência conservadora baseada na
  constituição.

### Escopo autorizado e bloqueios restantes

- A autorização de 2026-11-27 permite somente acesso pontual à API de metadados e download
  local de um item individual da Next Digital Library confirmado como parte do corpus
  Public Domain Mark. O aplicativo limita consultas de metadados a uma por minuto e
  imagens IIIF a até 12 por minuto; esses limites são locais, não cotas publicadas pela
  NDL. A NDL identifica uso
  contínuo como fora do acesso sem solicitação; por isso `periodic_catalog_updates_enabled`
  permanece falso.
- `B003-REAL-SOURCE` continua para MangaDex, outros catálogos, conteúdo sem PDM confirmado,
  republicação/distribuição e qualquer ampliação de escopo. A consulta e o download NDL não
  presumem compatibilidade com mangás serializados ou capítulos modernos.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| URL fornecida alcança serviço interno ou metadados de nuvem. | Validar IP literal, todas as respostas DNS e destino efetivo; recusar endereços não globalmente roteáveis antes da conexão. |
| Redirecionamento contorna a validação inicial. | Seguir somente redirects permitidos pela allowlist central; revalidar cada salto, limitar a cinco e detectar loops/downgrade. |
| DNS muda entre validação e conexão. | Garantir que o destino conectado seja o mesmo endereço público validado; falhar fechado em resposta mista ou inconsistente. |
| Provedor passa a acessar conteúdo não autorizado ou termos mudam. | Exigir evidência oficial por capacidade de download, guardar revisão/data e desativar a integração quando a permissão não estiver clara. |
| Correspondência parcial seleciona um host controlado por terceiro. | Usar host normalizado e regras explícitas por provedor; não confiar em substring ou sufixo implícito. |
| URL contém credencial ou token em query. | Rejeitar userinfo, não persistir URL e remover query/token de mensagens e logs. |
| Resposta do provedor viola ordem ou identidade de capítulos/páginas. | Validar identidade e ordenação; responder com `ProviderResponseInvalid` sem persistir dados parciais. |

### Fora do Escopo

- Provedor real MangaDex ou de qualquer outra fonte sem autorização específica verificável.
- Download NDL automático, periódico, em lote sem seleção, ou de conteúdo fora do corpus PDM.
- Conversão para Kindle; o download NDL é implementado pela F005.
- Login, armazenamento de credenciais, CAPTCHA, bypass de DRM, paywall ou restrição de
  acesso.
- Carregamento dinâmico de plugins de terceiros ou instalação de extensões pela pessoa
  usuária.
- Scraping genérico de sites sem API/documentação e autorização de uso.
- Testes que consultem uma fonte externa real ou usem credenciais/rede durante a suíte.

### Referências Verificadas

- [Documentação oficial da API MangaDex — política de uso aceitável](https://gitlab.com/mangadex-pub/mangadex-api-docs/-/raw/main/index.md), consultada em 2026-11-25. A política lista condições de crédito, retirada de conteúdo e não monetização; não esclarece exportação local dos capítulos.
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), consultada em 2026-11-25. Recomenda validar entradas de URL e não permitir redirecionamentos sem proteção contra contorno das validações.
