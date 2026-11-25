# Especificação de Funcionalidade: F001 — Fundação do Manga to Kindle

**Branch da funcionalidade**: `001-app-foundation`

**Criada em**: 2026-11-25

**Status**: Rascunho

**Entrada**: Fundação local do aplicativo, com configuração e diretórios do usuário,
logs rotativos, tratamento de exceções, SQLite e migrações; contratos Manga, Chapter,
Page, DownloadJob, DeviceProfile e Export; inicialização, encerramento seguro, testes e
README. Nenhuma rede real nesta funcionalidade.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Instalar e abrir pela primeira vez (Prioridade: P1)

Como pessoa usuária, quero instalar e abrir o Manga to Kindle em um perfil limpo do
Windows para começar com uma base local pronta e sem depender de conexão externa.

**Por que esta prioridade**: Sem uma primeira inicialização confiável, nenhuma
funcionalidade posterior pode ser usada.

**Teste independente**: Seguir as instruções do README em um ambiente limpo do Windows e
confirmar que a janela inicial aparece e que os diretórios e a base local são preparados.

**Cenários de aceitação**:

1. **Dado** um ambiente suportado e sem dados anteriores do aplicativo, **quando** a
   pessoa usuária inicia o Manga to Kindle, **então** a janela principal em português
   aparece e a estrutura local necessária é criada no perfil dessa pessoa.
2. **Dado** que o computador está sem conexão com a internet, **quando** a pessoa usuária
   inicia ou encerra o aplicativo, **então** o fluxo é concluído sem tentativa de acesso
   a serviços externos.
3. **Dado** que a primeira inicialização terminou, **quando** a pessoa usuária inicia o
   aplicativo novamente, **então** a configuração e a base existentes são reutilizadas
   sem reinicialização destrutiva.

### História 2 — Encerrar sem perder ou corromper dados (Prioridade: P1)

Como pessoa usuária, quero que o aplicativo encerre de forma segura para preservar a
configuração e os dados locais entre sessões.

**Por que esta prioridade**: A integridade dos dados locais é uma obrigação da
constituição e da base de qualquer funcionalidade futura.

**Teste independente**: Abrir, encerrar normalmente e reabrir o aplicativo em ciclos
repetidos; confirmar que a base continua íntegra e que os dados de configuração não são
substituídos por padrões.

**Cenários de aceitação**:

1. **Dado** um aplicativo inicializado, **quando** a pessoa usuária escolhe encerrar,
   **então** novas operações deixam de ser aceitas, as gravações em andamento são
   finalizadas ou revertidas com segurança e o processo termina sem deixar transações
   incompletas.
2. **Dado** que a base contém dados válidos, **quando** ocorre um encerramento normal e
   uma nova inicialização, **então** os dados continuam disponíveis e a versão do esquema
   permanece válida.

### História 3 — Entender e recuperar uma falha (Prioridade: P2)

Como pessoa usuária, quero receber uma mensagem clara quando a inicialização falhar para
saber se posso tentar novamente ou preciso de suporte, sem expor conteúdo dos meus livros.

**Por que esta prioridade**: Falhas em arquivos, configuração ou migrações não podem
resultar em perda silenciosa de dados nem em mensagens impossíveis de diagnosticar.

**Teste independente**: Injetar falhas de inicialização e migração e verificar a mensagem
em português, o registro local sanitizado e a preservação dos dados anteriores.

**Cenários de aceitação**:

1. **Dado** que a configuração ou a base não pode ser lida, **quando** a inicialização
   falha, **então** a interface informa o problema em linguagem clara e indica um próximo
   passo seguro, sem apagar o arquivo original.
2. **Dado** que uma migração falha, **quando** o aplicativo interrompe a inicialização,
   **então** a base permanece íntegra no esquema anterior e a falha é registrada sem
   segredos, credenciais ou conteúdo de livros.

### História 4 — Evoluir o catálogo com contratos consistentes (Prioridade: P2)

Como pessoa que mantém o produto, quero contratos de domínio estáveis para representar
mangás, capítulos, páginas, tarefas de download, perfis de dispositivo e exportações sem
duplicar regras de integridade em funcionalidades futuras.

**Por que esta prioridade**: A representação comum reduz inconsistências quando forem
especificadas as próximas features.

**Teste independente**: Validar cada contrato com casos válidos e inválidos, sem rede,
interface de catálogo ou geração de arquivos de exportação.

**Cenários de aceitação**:

1. **Dado** um Manga com Chapter e Page válidos, **quando** seus contratos são validados,
   **então** as relações e a ordem das páginas são consistentes.
2. **Dado** um DownloadJob ou Export, **quando** uma transição de estado inválida ou um
   progresso impossível é solicitado, **então** o contrato rejeita a mudança sem iniciar
   uma operação externa.

### Casos extremos

- O perfil do usuário não permite criar ou gravar em um dos diretórios necessários.
- O volume fica sem espaço durante a criação da configuração, da base ou de um log.
- A configuração local está ausente, incompleta ou malformada.
- A base já existe, está bloqueada por outro processo ou não corresponde a um arquivo
  SQLite válido.
- Uma migração falha depois de iniciar e deve ser revertida sem alterar o esquema anterior.
- O logger não consegue gravar ou rotacionar arquivos; a falha não pode ocultar a causa
  original nem travar a interface.
- Uma exceção ocorre antes da inicialização completa do logger ou durante o encerramento.
- Caminhos contêm espaços ou caracteres acentuados, ou têm comprimento próximo ao limite
  suportado pelo Windows.
- Um Page aponta para uma imagem ausente; a referência inválida não deve alterar nem
  substituir a imagem original.
- O progresso de um DownloadJob excede o total, apresenta total desconhecido ou tenta
  transicionar a partir de um estado terminal.
- Um Export não tem capítulo de origem, DeviceProfile válido ou destino local definido.
- O usuário tenta encerrar durante uma transação; a transação precisa ser finalizada ou
  revertida antes da saída.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A instalação documentada deve ser reproduzível em um ambiente limpo de
  Windows 10 e Windows 11 usando as versões de dependências registradas pelo projeto.
- **RF-002**: Na primeira inicialização, o aplicativo deve criar sob o diretório local do
  usuário uma raiz própria para o Manga to Kindle e as subpastas `config`, `data`, `logs`
  e `cache`. Repetir a inicialização deve ser idempotente.
- **RF-003**: A configuração local deve iniciar com valores seguros e persistir mudanças
  sem guardar credenciais ou conteúdo de livros. Uma configuração inválida deve ser
  preservada para diagnóstico, e o aplicativo não deve substituí-la silenciosamente.
- **RF-004**: O aplicativo deve criar e inicializar automaticamente uma base SQLite local
  na primeira execução, sem exigir uma ação manual de banco de dados.
- **RF-005**: O esquema local deve ter versão identificável. Na inicialização, migrações
  pendentes devem ser aplicadas antes de abrir a janela principal; executar o processo
  novamente no esquema atual não deve alterar nem duplicar dados.
- **RF-006**: Cada migração deve ser atômica ou recuperável. Se uma migração falhar, os
  dados existentes devem permanecer disponíveis no esquema anterior ou em uma cópia
  recuperável, e a aplicação deve informar que não iniciou normalmente.
- **RF-007**: O aplicativo deve registrar eventos operacionais e falhas em arquivos locais
  com rotação por tamanho. O padrão é até 5 MiB por arquivo e até três arquivos rotacionados,
  configurável localmente. Segredos, credenciais e conteúdo de livros não podem aparecer
  nos logs.
- **RF-008**: Exceções não tratadas na inicialização, na interface ou no encerramento
  devem ser capturadas na fronteira adequada, registradas de forma sanitizada e apresentadas
  à pessoa usuária em português claro. Uma falha essencial não deve deixar o aplicativo
  em estado parcialmente inicializado.
- **RF-009**: O encerramento normal deve parar novas operações, finalizar ou reverter
  gravações locais em andamento, fechar a base e liberar os recursos de logging antes de
  concluir.
- **RF-010**: Os contratos de domínio devem definir as seguintes entidades e suas
  invariantes mínimas:

  | Entidade | Contrato mínimo |
  |---|---|
  | `Manga` | Identidade estável, título obrigatório e coleção ordenável de capítulos; referência a uma fonte externa é opcional e não implica acesso à rede. |
  | `Chapter` | Identidade estável, vínculo a um `Manga`, título ou número de exibição e posição de leitura não ambígua dentro do mangá. |
  | `Page` | Identidade estável, vínculo a um `Chapter`, posição única dentro do capítulo e referência local à imagem original; o contrato nunca autoriza sobrescrever essa imagem. |
  | `DownloadJob` | Identidade, alvo de mangá ou capítulo, estado, progresso e pedido de cancelamento; estados terminais não podem voltar a execução e o progresso não pode ser negativo nem exceder um total conhecido. Nesta feature não inicia downloads. |
  | `DeviceProfile` | Identidade, nome e preferências de saída validadas; o contrato não presume um modelo Kindle ou capacidade de dispositivo específica. |
  | `Export` | Identidade, uma ou mais referências de conteúdo, perfil de dispositivo, destino local e estado; representa somente o pedido de exportação, sem gerar arquivo ou enviar conteúdo nesta feature. |

- **RF-011**: A inicialização, o encerramento e a suíte de testes desta feature não devem
  fazer requisições reais, downloads, autenticações ou qualquer outra chamada de rede.
- **RF-012**: O README deve documentar a instalação reproduzível, a inicialização,
  diretórios e localização dos dados, logs, comandos de qualidade e execução dos testes,
  além dos limites de rede desta feature.
- **RF-013**: Testes automatizados devem cobrir primeira inicialização, repetição da
  inicialização, encerramento, criação de diretórios, configuração, migrações bem-sucedidas
  e com falha, rotação de logs, exceções, contratos de domínio e ausência de tráfego de rede.

### Requisitos Não Funcionais

- **RNF-001**: O produto alvo é Windows 10/11, Python 3.12 ou superior e PySide6. O ambiente
  e as dependências devem ser gerenciados por `uv`; Ruff, MyPy e Pytest são as ferramentas
  de lint, tipagem e testes definidas pela constituição.
- **RNF-002**: Nenhuma operação potencialmente bloqueante de disco ou banco pode bloquear
  a thread gráfica.
- **RNF-003**: Dados e configuração devem permanecer no dispositivo e no perfil do usuário;
  logs não podem conter segredos, credenciais ou conteúdo de livros.
- **RNF-004**: A interface e a documentação do usuário devem estar em português brasileiro;
  código, símbolos e identificadores devem estar em inglês.
- **RNF-005**: Em um perfil limpo de referência do projeto, a janela principal deve ficar
  disponível em até 10 segundos após o início do aplicativo.

### Entidades Principais

Os seis contratos e invariantes são definidos em **RF-010**. São contratos conceituais
para orientar features posteriores; esta especificação não determina APIs, classes ou
estrutura interna de módulos.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: Em ambientes limpos de Windows 10 e Windows 11, o procedimento documentado
  instala as dependências de forma reproduzível e inicia a janela principal em até
  10 segundos no perfil de referência.
- **CS-002**: Em 10 ciclos consecutivos de abrir e encerrar, existe uma única base ativa,
  os quatro diretórios locais permanecem no perfil do usuário e nenhum dado já persistido
  é removido ou reinicializado.
- **CS-003**: A inicialização, o encerramento e a suíte automatizada produzem zero chamadas
  externas de rede.
- **CS-004**: A rotação ocorre ao atingir o limite configurado de 5 MiB e mantém no máximo
  três arquivos rotacionados; os testes confirmam que logs não contêm segredos, credenciais
  ou conteúdo de livros.
- **CS-005**: Os testes de migração confirmam inicialização idempotente e preservação dos
  dados anteriores quando uma migração falha.
- **CS-006**: Testes dos seis contratos aceitam todos os casos válidos e rejeitam todos os
  estados inválidos definidos em RF-010.
- **CS-007**: Todos os cenários de aceitação desta especificação passam nos testes da
  feature, e o README permite que outra pessoa reproduza a instalação e a execução local.

## Premissas

- “Instalação reproduzível” nesta feature significa preparar o ambiente local a partir das
  dependências e versões registradas pelo projeto; não inclui gerar instalador MSI ou EXE.
- A raiz local do aplicativo fica na área de dados locais do perfil do usuário no Windows,
  com as subpastas `config`, `data`, `logs` e `cache`.
- Os padrões de rotação são 5 MiB por arquivo e três cópias anteriores; podem ser revistos
  na fase de planejamento se a política do produto exigir outros limites.
- Não há banco ou dados legados a migrar. A feature cria a versão inicial do esquema e
  estabelece o comportamento para migrações futuras.
- `DownloadJob`, `DeviceProfile` e `Export` são contratos de domínio nesta feature; não
  habilitam download real, detecção de dispositivo, geração de arquivo ou envio ao Kindle.
- Não encontrei `docs/roadmap.md` nem especificações locais de features anteriores. O
  projeto MCP informado também não possui features ou tarefas registradas. F001 é tratada
  como fundação sem predecessores conhecidos; dependências de F002 em diante não são
  inferidas aqui.

## Dependências, Riscos e Limites de Escopo

### Dependências

- A constituição em [`../../.specify/memory/constitution.md`](../../.specify/memory/constitution.md)
  é a fonte normativa de arquitetura, privacidade, idiomas e qualidade.
- O procedimento de instalação deve respeitar Python 3.12+, PySide6, `uv`, Ruff, MyPy,
  Pytest e SQLite. Versões e APIs devem ser verificadas na documentação oficial e no
  ambiente resolvido do projeto antes do planejamento técnico.
- Não há dependência conhecida de feature anterior. Features de catálogo, download e
  exportação dependem dos contratos e da persistência definidos por F001; seus vínculos
  específicos devem ser registrados nas respectivas specs.
- O README raiz deve ser atualizado durante a implementação desta feature, não nesta
  etapa de especificação.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Permissões, caminhos ou espaço em disco impedem o uso do perfil local. | Detectar a falha antes de apresentar a inicialização como concluída; mostrar o local e a ação segura em português. |
| Migração incompleta pode danificar dados futuros. | Aplicar migrações de modo atômico ou recuperável e testar falha após cada etapa relevante. |
| Logs podem vazar credenciais, caminhos sensíveis ou conteúdo de livros. | Sanitizar dados antes da gravação e testar explicitamente conteúdo e segredos conhecidos. |
| Inicialização pode travar a interface durante operações locais. | Fazer I/O potencialmente bloqueante fora da thread gráfica e validar que a janela continua responsiva. |
| A configuração local pode ser sobrescrita por padrões após erro. | Preservar a configuração inválida e exigir ação explícita para substituí-la. |
| “Instalação” pode significar instalador distribuível, não ambiente reproduzível. | Esta spec assume ambiente local via dependências registradas; MSI/EXE está fora do escopo até decisão específica. |

### Fora do Escopo

- Qualquer acesso real a fontes externas, download de capítulos ou autenticação.
- Contorno de DRM, CAPTCHA, autenticação ou outras restrições de acesso.
- Processamento ou alteração de imagens originais.
- Geração de EPUB, MOBI ou outro arquivo de exportação.
- Descoberta, conexão ou envio de livros para um Kindle ou outro dispositivo.
- Telemetria, atualização automática ou comunicação com serviços remotos.
- Instalador distribuível MSI/EXE e interface completa de preferências ou catálogo.
