# Especificação de Funcionalidade: F002 — Interface Desktop do Manga to Kindle

**Branch da funcionalidade**: `002-desktop-interface`

**Criada em**: 2026-11-25

**Status**: Rascunho

**Entrada**: Interface PySide6 em português com tema claro/escuro e navegação por
Biblioteca, Adicionar mangá, Downloads, Conversão e Configurações. Inclui URL, seleção
múltipla de capítulos, pasta de saída, perfil Kindle e formato; estados vazios,
carregando, erro e sucesso; acessibilidade por teclado; dados simulados claramente
identificados até a integração de serviços reais. Nenhuma implementação nesta etapa.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Navegar pela biblioteca e pelas áreas do aplicativo (Prioridade: P1)

Como pessoa usuária, quero encontrar as áreas principais do aplicativo e entender quando
a biblioteca está vazia para saber como começar.

**Por que esta prioridade**: Navegação clara e estado vazio são a entrada para todos os
fluxos desta interface.

**Teste independente**: Abrir cada área da navegação e confirmar que o conteúdo, o foco do
teclado e o estado correspondente aparecem sem conexão externa.

**Cenários de aceitação**:

1. **Dado** que a janela está aberta, **quando** a pessoa usuária seleciona Biblioteca,
   Adicionar mangá, Downloads, Conversão ou Configurações, **então** o título e o conteúdo
   da área selecionada aparecem em português.
2. **Dado** que não há mangás, capítulos ou tarefas de demonstração carregados,
   **quando** a pessoa usuária abre Biblioteca ou Downloads, **então** vê um estado vazio
   com uma ação inicial adequada, sem mensagens que indiquem falha.
3. **Dado** qualquer área da interface, **quando** a pessoa usuária percorre a navegação
   pelo teclado, **então** o foco é visível e cada destino pode ser aberto sem mouse.

### História 2 — Adicionar um mangá de demonstração e escolher capítulos (Prioridade: P1)

Como pessoa usuária, quero informar uma URL e selecionar vários capítulos para entender o
fluxo de entrada antes da conexão com serviços reais.

**Por que esta prioridade**: O campo de URL e a seleção múltipla são o principal fluxo de
entrada do catálogo, mas precisam deixar claro que ainda não acessam a fonte.

**Teste independente**: Informar uma URL sintaticamente válida, acompanhar o estado de
carregamento simulado e selecionar e desmarcar capítulos com teclado e mouse.

**Cenários de aceitação**:

1. **Dado** um endereço HTTP ou HTTPS sintaticamente válido, **quando** a pessoa usuária
   solicita a consulta, **então** a interface apresenta carregamento e resultados
   identificados como dados de demonstração, sem fazer uma requisição externa.
2. **Dado** uma lista de pelo menos cinco capítulos simulados, **quando** a pessoa usuária
   seleciona três capítulos e desmarca um, **então** o resumo mostra exatamente dois
   capítulos selecionados e a seleção pode ser feita inteiramente pelo teclado.
3. **Dado** um campo vazio ou um endereço inválido, **quando** a pessoa usuária solicita a
   consulta, **então** recebe um erro acionável em português e nenhum endereço completo é
   gravado em logs ou enviado à rede.

### História 3 — Acompanhar downloads e conversões simulados (Prioridade: P1)

Como pessoa usuária, quero acompanhar progresso, sucesso, falha ou cancelamento para
entender como serão apresentados os trabalhos futuros.

**Por que esta prioridade**: Os fluxos de Downloads e Conversão são operações demoradas e
devem estabelecer o padrão de responsividade antes de integrações reais.

**Teste independente**: Iniciar uma operação de demonstração, observar progresso, navegar
para outra área e cancelar a operação sem bloquear a janela.

**Cenários de aceitação**:

1. **Dado** um DownloadJob simulado, **quando** a pessoa usuária abre Downloads,
   **então** vê estado, progresso e a identificação persistente de que os dados são
   simulados.
2. **Dado** capítulos selecionados, uma pasta de saída existente, um perfil de
   demonstração e um formato de demonstração, **quando** a pessoa usuária inicia a
   conversão, **então** acompanha progresso e recebe um resultado descrito como simulado;
   nenhum arquivo é gerado.
3. **Dado** um trabalho simulado em andamento, **quando** a pessoa usuária cancela,
   **então** o estado muda para cancelado, o progresso para e a janela continua
   respondendo.

### História 4 — Personalizar a aparência e operar sem mouse (Prioridade: P2)

Como pessoa usuária, quero escolher tema claro ou escuro e usar as funções principais com
teclado para adaptar a interface às minhas preferências.

**Por que esta prioridade**: Aparência e acessibilidade tornam os fluxos principais
utilizáveis em diferentes condições de uso.

**Teste independente**: Alternar tema, reiniciar a aplicação e completar navegação,
seleção de capítulos e conversão simulada usando somente teclado.

**Cenários de aceitação**:

1. **Dado** que a pessoa usuária escolhe tema claro ou escuro, **quando** troca de área e
   reinicia o aplicativo, **então** o tema escolhido permanece aplicado.
2. **Dado** que a pessoa usuária usa somente teclado, **quando** percorre cada fluxo
   principal, **então** consegue chegar aos controles, alterar seleções, confirmar ou
   cancelar ações e perceber o foco atual.

### Casos extremos

- URL vazia, malformada, com esquema diferente de HTTP/HTTPS ou contendo credenciais.
- A consulta simulada não retorna capítulos ou retorna muitos capítulos e títulos longos.
- Nenhum capítulo está selecionado ou todos foram desmarcados antes de iniciar a conversão.
- A pasta de saída não existe, está sem permissão ou contém espaços e caracteres
  acentuados no caminho.
- A lista simulada de perfis ou formatos está vazia ou contém uma opção inválida.
- A demonstração retorna estado de erro, sucesso imediato ou progresso interrompido.
- O cancelamento ocorre antes do início, durante o progresso ou após um estado terminal.
- A pessoa usuária troca de área ou de tema durante um trabalho simulado.
- O foco do teclado se perde ao abrir ou fechar diálogos; uma área não tem controles
  alcançáveis por teclado.
- A janela é redimensionada, usada em tela pequena ou exibida com escala ampliada do
  Windows.
- O computador está sem rede; a interface deve continuar funcionando sem tentativas de
  conexão.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A interface deve oferecer navegação para Biblioteca, Adicionar mangá,
  Downloads, Conversão e Configurações, com indicação clara da área ativa.
- **RF-002**: Biblioteca deve apresentar estado vazio quando não houver dados e uma
  visualização de itens de demonstração quando houver fixtures carregadas; cada item
  simulado deve estar identificado como tal.
- **RF-003**: Adicionar mangá deve oferecer campo URL e validar apenas formato e esquema
  HTTP/HTTPS. Consultar não pode validar disponibilidade da fonte nem fazer acesso remoto.
- **RF-004**: Após uma consulta válida, a interface deve exibir um mangá e capítulos de
  demonstração, com aviso visível de que serviços reais ainda não estão conectados.
- **RF-005**: A lista de capítulos deve permitir selecionar e desmarcar múltiplos itens
  por mouse e teclado, indicar a quantidade selecionada e preservar a seleção durante o
  fluxo de conversão.
- **RF-006**: Downloads deve exibir estados vazio, carregando, erro, em andamento,
  concluído e cancelado com texto e progresso compreensíveis. Os trabalhos são simulados e
  podem ser cancelados enquanto estiverem em andamento.
- **RF-007**: Conversão deve permitir selecionar capítulos, escolher uma pasta de saída,
  um perfil Kindle de demonstração e um formato de demonstração; cada campo obrigatório
  deve ser validado antes de iniciar.
- **RF-008**: Conversão deve apresentar progresso e resultados de sucesso, erro ou
  cancelamento explicitamente simulados. Esta feature não gera arquivo nem envia conteúdo
  a qualquer dispositivo ou serviço.
- **RF-009**: Biblioteca, Adicionar mangá, Downloads e Conversão devem exibir estados
  vazios, carregando, erro e sucesso quando aplicáveis, com ações de recuperação em erros
  corrigíveis.
- **RF-010**: Configurações deve permitir alternar entre tema claro e escuro e persistir a
  preferência usando a configuração local fornecida por F001. O padrão inicial é claro.
- **RF-011**: Todos os controles interativos devem ser acessíveis por teclado, com foco
  visível e rótulos em português. A lista de capítulos deve aceitar navegação por setas e
  seleção/desmarcação por Espaço; ações focadas devem poder ser ativadas por Enter ou
  Espaço conforme seu tipo.
- **RF-012**: Uma identificação persistente de “Dados simulados — serviços reais ainda
  não conectados” deve acompanhar listas e operações de demonstração em todas as áreas
  relevantes. Resultados simulados não podem ser apresentados como downloads ou conversões
  reais.
- **RF-013**: A URL digitada deve permanecer apenas no fluxo local de demonstração; não
  deve ser enviada à rede nem gravada em logs. O erro de validação não deve ecoar a URL
  completa.
- **RF-014**: Operações simuladas devem permitir progresso, cancelamento seguro e estados
  previsíveis sem bloquear a navegação ou a janela principal.
- **RF-015**: Testes automatizados devem cobrir navegação, estados, validação de URL,
  seleção múltipla por mouse e teclado, tema persistente, pasta/perfil/formato, progresso,
  cancelamento, rótulos de demonstração e ausência de chamadas de rede ou arquivos gerados.
- **RF-016**: O README deve documentar as cinco áreas, o modo de demonstração, as ações que
  ainda não acessam serviços reais e a navegação por teclado.

### Requisitos Não Funcionais

- **RNF-001**: A interface deve usar PySide6, seguir a constituição F001 e ser compatível
  com Windows 10 e Windows 11.
- **RNF-002**: A janela deve responder a navegação, seleção e cancelamento em até 200 ms
  enquanto uma operação simulada está em progresso, medido no perfil de teste de
  referência.
- **RNF-003**: Nenhum I/O ou processamento potencialmente bloqueante deve ocorrer na
  thread gráfica. Os trabalhos devem informar progresso e aceitar cancelamento quando
  seguros.
- **RNF-004**: O texto da interface deve estar em português brasileiro; estados não devem
  depender exclusivamente de cor para comunicar sucesso, erro ou progresso.
- **RNF-005**: Fluxos principais devem ser completáveis sem mouse; foco e estado de seleção
  devem permanecer perceptíveis nos temas claro e escuro.
- **RNF-006**: O modo desta feature deve funcionar sem conexão e produzir zero requisições
  de rede, downloads, conversões reais ou transferências de livros.

### Entidades Principais

- **Manga e Chapter**: Entidades de F001 exibidas como dados simulados; a seleção de
  capítulos usa a identidade e a ordem definidas pelos contratos existentes.
- **DownloadJob**: Entidade de F001 apresentada com estado e progresso simulados; não
  representa acesso a uma fonte ou arquivo baixado.
- **DeviceProfile e Export**: Entidades de F001 usadas apenas para seleção e prévia
  simuladas; nenhuma compatibilidade real de modelo/formato é afirmada e nenhum arquivo é
  produzido.
- **Page**: Contrato de F001 sem visualização ou processamento de imagens nesta feature.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: As cinco áreas podem ser abertas por mouse e teclado; cada resposta de
  navegação ocorre em até 200 ms no perfil de referência.
- **CS-002**: Em uma lista de cinco capítulos simulados, a pessoa usuária consegue marcar
  três e desmarcar um por teclado; o resumo final corresponde exatamente aos dois itens
  restantes.
- **CS-003**: Durante uma operação simulada de 30 segundos, navegação, seleção e
  cancelamento continuam respondendo em até 200 ms, sem travar a janela.
- **CS-004**: Cada fluxo principal demonstra estados vazio, carregando, erro e sucesso
  aplicáveis; 100% dos itens ou resultados de demonstração exibem identificação de dados
  simulados.
- **CS-005**: A preferência de tema claro ou escuro permanece após duas reinicializações
  consecutivas.
- **CS-006**: Os testes desta feature confirmam zero requisições de rede, zero arquivos
  exportados e zero transferências de livros.
- **CS-007**: Os cenários de aceitação passam em Windows 10 e Windows 11 e o README permite
  distinguir claramente os fluxos simulados dos serviços ainda não integrados.

## Premissas

- F002 depende de F001 implementada: inicialização da aplicação, configuração local,
  logging, tratamento de exceções e contratos de domínio devem estar disponíveis.
- Não encontrei `docs/roadmap.md`; o checkout contém a especificação F001, que declara não
  haver predecessores conhecidos. A dependência F002 → F001 é explícita neste documento;
  a ordem e dependências posteriores não são inferidas.
- As listas de mangás, capítulos, trabalhos, perfis e formatos são fixtures de demonstração
  determinísticas, exibidas com identificação persistente. Elas não são gravadas como
  conteúdo real da biblioteca.
- A URL só é validada sintaticamente e não é persistida nesta feature. Nenhum perfil ou
  formato de demonstração representa promessa de compatibilidade Kindle.
- A pasta de saída é escolhida para a operação, validada localmente e não recebe arquivos
  nesta feature. O tema é a única preferência visual que deve ser persistida aqui.
- O tema inicial é claro; a preferência escolhida é armazenada na configuração local de
  F001.
- O ponto de responsividade de 200 ms e a simulação de 30 segundos são metas verificadas
  em máquinas de teste de referência; os detalhes de ambiente devem ser definidos no
  planejamento.

## Dependências, Riscos e Limites de Escopo

### Dependências

- A constituição em [`../../.specify/memory/constitution.md`](../../.specify/memory/constitution.md)
  define idioma, arquitetura, privacidade e responsividade. O requisito de acessibilidade
  por teclado vem do pedido desta feature.
- F001 — [Fundação do Manga to Kindle](../001-app-foundation/spec.md) fornece a base de
  inicialização, persistência de configuração, tratamento de falhas e contratos Manga,
  Chapter, Page, DownloadJob, DeviceProfile e Export.
- As integrações de fonte e de conversão ainda não existem nesta feature; as fixtures
  simuladas são a única fonte de dados dos fluxos.
- O README raiz deve ser atualizado na implementação de F002 para explicar navegação,
  modo de demonstração e uso por teclado; esta etapa altera somente a especificação.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| A pessoa usuária confunde resultados simulados com dados reais. | Manter aviso visível em todas as áreas e rotular cada item e resultado de demonstração. |
| Uma URL sensível é registrada ou enviada acidentalmente. | Não persistir nem registrar a URL completa e testar zero chamadas de rede. |
| Trabalho de demonstração bloqueia a interface e mascara riscos de integração futura. | Exercitar progresso/cancelamento e medir resposta da janela enquanto a simulação está ativa. |
| Tema escuro reduz contraste ou estados dependem apenas da cor. | Verificar rótulos, foco visível e indicadores textuais nos dois temas. |
| Seleção múltipla funciona com mouse, mas não com teclado. | Cobrir seleção, remoção e navegação em testes usando apenas teclado. |
| Perfil ou formato fictício cria expectativa de suporte a um Kindle real. | Marcar as opções como demonstração e não afirmar compatibilidade nesta feature. |

### Fora do Escopo

- Chamadas reais a URLs, scraping, autenticação, downloads ou consulta de fontes externas.
- Contorno de DRM, CAPTCHA, login, paywall ou restrições de acesso.
- Persistência de mangás ou capítulos simulados como conteúdo real da biblioteca.
- Geração ou conversão real de arquivos, escrita na pasta de saída e envio a Kindle.
- Detecção de dispositivo, validação de compatibilidade de perfil/formato ou catálogo real
  de formatos suportados.
- Telemetria, sincronização em nuvem, conta de usuário e atualização automática.
