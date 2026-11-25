# Especificação de Funcionalidade: F010 — Atualização de Capítulos do Manga to Kindle

**Feature Branch**: `010-chapter-updates`

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Permitir atualização manual do catálogo de capítulos e verificação periódica opcional enquanto o aplicativo estiver aberto. Respeitar capacidades, termos e limites declarados por cada fonte, identificar capítulos novos por identidade estável e emitir notificações locais. Não baixar nem enviar capítulos automaticamente. Testar catálogo alterado, duplicatas, indisponibilidade e desativação.

## Histórias de Usuário e Testes

### História 1 — Atualizar capítulos manualmente (Prioridade: P1)

Como pessoa usuária, quero atualizar o catálogo de um mangá quando eu decidir, para ver capítulos novos sem baixar conteúdo automaticamente.

**Por que esta prioridade**: O controle manual oferece atualização previsível e útil mesmo quando a verificação periódica está desligada.

**Teste independente**: Consultar um catálogo de fixture, atualizar sua lista e conferir a ordenação, IDs, seleção e preservação de dados anteriores quando a fixture falhar.

**Cenários de aceitação**:

1. **Dado** um mangá ligado a provedor habilitado e uma resposta completa com IDs já conhecidos e novos, **quando** a pessoa usuária escolhe “Atualizar capítulos”, **então** o catálogo é atualizado uma única vez, preserva IDs existentes, insere os novos e os ordena segundo F004.
2. **Dado** falha, indisponibilidade, limite vigente, resposta parcial ou cancelamento, **quando** a atualização não termina com catálogo válido, **então** o último catálogo completo permanece intacto e a interface informa o resultado sem apagar capítulos ou arquivos.
3. **Dado** que não existe fonte autorizada habilitada para o mangá, **quando** a pessoa usuária tenta atualizar, **então** a interface explica que a consulta real não está disponível e não inicia tráfego de rede nem apresenta fixture como resultado real.

### História 2 — Monitorar capítulos em intervalo configurável (Prioridade: P2)

Como pessoa usuária, quero ativar a verificação periódica para mangás escolhidos e definir um intervalo, para acompanhar novidades enquanto o Manga to Kindle estiver aberto.

**Por que esta prioridade**: A rotina automática reduz consultas repetidas pela pessoa usuária, mas precisa permanecer opcional e subordinada às regras de cada fonte.

**Teste independente**: Usar relógio e provedor simulados para ativar o monitoramento, avançar o tempo, conferir chamadas no vencimento e verificar que desligar a opção ou encerrar o aplicativo para futuras consultas.

**Cenários de aceitação**:

1. **Dado** que monitoramento está desligado por padrão, **quando** o aplicativo inicia, **então** nenhuma consulta periódica ocorre.
2. **Dado** que a pessoa usuária habilita monitoramento para um mangá, define intervalo e a fonte declara limites compatíveis, **quando** o intervalo efetivo vence enquanto o aplicativo está aberto, **então** uma consulta de catálogo é executada, respeitando o máximo de chamadas e concorrência da fonte.
3. **Dado** que a fonte não declara limites ou capacidade de consulta periódica, **quando** a pessoa usuária tenta habilitar monitoramento, **então** o aplicativo mantém a rotina desabilitada para essa fonte e explica o motivo; a aplicação não inventa frequência permitida.
4. **Dado** que o aplicativo fica fechado ou uma consulta é perdida durante suspensão, **quando** ele é encerrado ou retorna, **então** não há serviço externo em segundo plano nem rajada de consultas atrasadas; no máximo uma consulta vencida por mangá elegível pode ser programada após o retorno, respeitando todos os limites.
5. **Dado** que a pessoa usuária desabilita o monitoramento durante uma consulta, **quando** o cancelamento seguro é possível, **então** a consulta é cancelada; caso contrário, a resposta pode ser validada e gravada uma única vez, mas nenhuma verificação futura é agendada.

### História 3 — Identificar e receber avisos de capítulos novos (Prioridade: P2)

Como pessoa usuária, quero receber um aviso local quando um catálogo já conhecido ganhar capítulos com novas identidades, para escolher quais capítulos baixar depois.

**Por que esta prioridade**: Identidade estável separa novidades reais de mudanças de título, posição ou ordem e evita avisos repetidos.

**Teste independente**: Carregar uma lista inicial de fixture, depois uma lista com IDs antigos, duplicados e novos; conferir avisos únicos e a ausência de DownloadJob ou envio criado pelo aviso.

**Cenários de aceitação**:

1. **Dado** o primeiro catálogo válido de um mangá, **quando** ele é salvo, **então** a lista é registrada como linha de base, sem notificar cada capítulo como novidade.
2. **Dado** um catálogo atualizado com IDs existentes repetidos, **quando** a resposta é processada, **então** nenhum capítulo duplicado nem notificação repetida é criado.
3. **Dado** um catálogo posterior com novo ID estável, **quando** a atualização é concluída, **então** uma notificação local por mangá resume os novos capítulos e abre a lista correspondente; não inicia download nem transferência.
4. **Dado** um capítulo existente com o mesmo ID, mas título, volume ou posição revisados, **quando** o catálogo é atualizado, **então** seus metadados são atualizados sem tratá-lo como novo nem apagar estado local.

### História 4 — Revisar estado e controlar notificações (Prioridade: P3)

Como pessoa usuária, quero consultar a última verificação e controlar avisos por mangá, para entender se o catálogo está atualizado ou se uma fonte falhou.

**Por que esta prioridade**: O estado local permite distinguir catálogo antigo de ausência real de novidades sem expor informações fora do dispositivo.

**Teste independente**: Consultar histórico de verificações simuladas bem-sucedidas, falhas e limitadas após reabrir o aplicativo; conferir timestamps, estado, contagem e preferência de avisos.

**Cenários de aceitação**:

1. **Dado** uma consulta concluída ou falha, **quando** a pessoa usuária abre os detalhes do mangá, **então** vê última tentativa, resultado e se os dados visíveis continuam sendo a última versão válida.
2. **Dado** que a pessoa usuária silencia avisos de um mangá ou marca um aviso como lido, **quando** novas verificações são executadas, **então** a preferência é preservada e não há notificação duplicada para IDs já conhecidos.

### Casos extremos

- A resposta completa muda título, número, volume, data ou ordem de um capítulo sem mudar seu ID estável.
- A resposta repete um mesmo ID com os mesmos dados ou com metadados conflitantes; contém IDs vazios, instáveis ou duplicados após normalização.
- Um capítulo possui número decimal, especial ou ausente, inclusive casos cobertos pelas regras de desempate de F004.
- A fonte retorna catálogo parcial, paginação incompleta, cursor repetido, timeout, erro de validação ou desconecta durante a leitura.
- A fonte fica indisponível, responde com limite temporário, `Retry-After`, acesso negado, autenticação, CAPTCHA ou alteração de termos.
- A fonte não oferece capacidade de consulta de capítulos, limite documentado ou permissão verificável para consultas recorrentes.
- Um mangá perde o vínculo com seu provedor, muda de URL, tem identidade da fonte alterada ou deixa de ser suportado.
- A resposta não lista capítulo antigo; a fonte não informa se a omissão significa remoção ou apenas catálogo incompleto.
- O usuário clica em atualizar enquanto uma verificação manual/periódica do mesmo mangá ou provedor está ativa.
- Vários mangás do mesmo provedor vencem ao mesmo tempo e a concorrência disponível é menor que a quantidade de verificações.
- O relógio do sistema muda, o aplicativo fica suspenso, hiberna, perde rede ou reabre depois do horário previsto.
- O aplicativo é encerrado ou o sistema fica sem espaço entre a resposta do provedor e a gravação local.
- A pessoa usuária desativa monitoramento ou notificações com verificações em fila, durante uma conexão ou após o catálogo ter sido atualizado.
- Uma notificação é criada mas não lida antes do reinício; um capítulo novo aparece em mais de uma página da resposta.
- O capítulo existe na biblioteca como importação local, mas não possui vínculo comprovável ao ID estável do provedor.
- Vários provedores usam o mesmo ID textual, número de capítulo ou título.
- O erro, URL, nome de capítulo ou retorno do provedor contém tokens, conteúdo sensível ou dados que não podem aparecer em logs.

## Requisitos

### Requisitos Funcionais

- **RF-001**: A Biblioteca deve oferecer atualização manual por mangá quando existir um provedor registrado com capacidade de consultar capítulos e autorização documentada para a consulta.
- **RF-002**: A atualização deve consultar somente o catálogo/metadados de capítulos do provedor; não deve buscar páginas, imagens, arquivos ou conteúdo de capítulo.
- **RF-003**: F010 deve usar as regras de URL, registro, erros, validação de destinos e capacidades de F003. Nenhum host arbitrário, provedor não registrado ou rota alternativa pode ser consultado.
- **RF-004**: A verificação de catálogo por rede só pode ser habilitada quando o uso de metadados, os termos aplicáveis e os limites de requisição estiverem documentados e aprovados. F010 não remove `B003-REAL-SOURCE` nem cria uma integração real com base em fixtures; se nenhuma fonte atender aos requisitos, o fluxo real permanece indisponível.
- **RF-005**: A aplicação deve incluir testes determinísticos com provedor/transportes de fixture identificados como simulados. Fixtures nunca podem aparecer como catálogo de fonte real nem habilitar tráfego remoto em produção.
- **RF-006**: IDs de capítulos devem permanecer estáveis e qualificados pelo provedor e pela identidade da fonte, conforme F004. Título, número de exibição, posição ou URL temporária não podem, isoladamente, determinar se um capítulo é novo.
- **RF-007**: Quando o provedor não fornecer ID estável, a aplicação só pode usar identificador canônico se a capacidade do provedor documentar sua estabilidade e unicidade. Sem prova suficiente, o item deve ser marcado como não identificável para novidades e não deve gerar notificação automática.
- **RF-008**: Uma resposta completa e válida deve reconciliar IDs conhecidos e novos de forma idempotente. Repetir a mesma lista deve gerar zero capítulos e zero avisos duplicados.
- **RF-009**: Um ID repetido dentro da resposta deve ser consolidado apenas se os dados estruturais forem consistentes. Conflito de ID/metadados, identidade vazia ou estrutura inválida deve rejeitar o catálogo inteiro sem gravação parcial.
- **RF-010**: Um capítulo conhecido com ID mantido deve conservar a identidade local e seus vínculos de arquivos, favoritos, seleção e histórico; apenas metadados de catálogo efetivamente fornecidos podem ser atualizados.
- **RF-011**: Capítulos novos devem iniciar sem seleção para download. Campos ausentes devem permanecer ausentes; número, título, idioma, volume ou disponibilidade não podem ser inventados.
- **RF-012**: A lista reconciliada deve conservar as regras de ordenação numérica, decimal, especial e de desempate de F004. Os mesmos dados de catálogo devem produzir a mesma ordem.
- **RF-013**: A primeira resposta completa válida deve estabelecer a linha de base sem notificar todos os itens preexistentes. Em verificações posteriores, somente IDs estáveis não registrados anteriormente podem gerar aviso de novidade.
- **RF-014**: Cada conjunto de IDs novos deve criar no máximo um aviso local por mangá e atualização concluída. Retornar a mesma identidade em outra verificação não deve recriar o aviso; estados lido/silenciado devem ser persistidos.
- **RF-015**: Avisos devem ser exibidos localmente na aplicação em português, indicar título/número somente quando fornecidos e permitir abrir a lista de capítulos. Não podem conter página/imagem nem ser enviados a serviços de push ou nuvem.
- **RF-016**: A aplicação deve oferecer uma ação manual “Atualizar capítulos” mesmo com monitoramento periódico desligado, desde que a consulta esteja autorizada e não viole um limite ou cooldown vigente.
- **RF-017**: O monitoramento periódico deve começar desligado e exigir habilitação explícita, seleção dos mangás monitorados e escolha de intervalo. Preferências e última verificação devem persistir localmente.
- **RF-018**: A rotina periódica deve executar somente enquanto o processo do aplicativo estiver ativo. Fechar o aplicativo interrompe a agenda; não deve instalar serviço, tarefa agendada do Windows, processo residente ou consulta quando fechado.
- **RF-019**: O intervalo efetivo por provedor/mangá nunca pode ser menor que o menor intervalo permitido, janela de limite ou política declarada pela fonte. Se a fonte não declarar capacidade ou limite necessário, monitoramento periódico deve permanecer indisponível para ela, sem frequência presumida.
- **RF-020**: Verificações manuais e periódicas devem respeitar rate limit, concorrência, timeout e cooldown de F003/F005. Uma resposta `Retry-After` válido deve persistir o próximo horário permitido; nenhuma consulta manual ou automática pode ignorá-lo.
- **RF-021**: A aplicação não deve agendar chamadas concorrentes para o mesmo mangá. Chamadas simultâneas do mesmo provedor devem respeitar a concorrência declarada e chamadas que apontem para o mesmo mangá devem ser consolidadas em uma única consulta em andamento.
- **RF-022**: O agendador deve evitar rajadas: verificações vencidas enquanto o aplicativo estava fechado ou suspenso não podem ser reproduzidas em lote. Após retorno, no máximo uma verificação vencida por mangá elegível pode ser colocada na fila; chamadas da fila devem ser escalonadas e respeitar o espaçamento e o limite agregado por provedor.
- **RF-023**: Falha de rede, indisponibilidade, rate limit, cancelamento, resposta parcial ou erro de validação deve preservar o último catálogo válido, IDs, seleção e arquivos locais. A tela deve indicar o horário da última versão válida e o resultado da tentativa atual.
- **RF-024**: Se uma resposta completa confirmar explicitamente que um capítulo deixou de existir, o registro pode ser marcado como indisponível na fonte, mas não excluído. Omissão em resposta parcial ou sem garantia de completude não deve alterar disponibilidade nem apagar dados.
- **RF-025**: O trabalho de rede, validação e persistência deve ocorrer fora da thread gráfica, apresentar progresso/estado e permitir cancelar a atualização manual ou desligar monitoramento quando for seguro. Ao cancelar, dados parciais não podem ser publicados.
- **RF-026**: Os estados devem distinguir ao menos nunca verificado, aguardando intervalo, consultando, atualizado sem novidades, atualizado com novidades, limitado/adiado, falha, cancelado e dados anteriores preservados.
- **RF-027**: Verificações, agenda, IDs de novidades, notificações e último horário devem ser persistidos localmente com migração versionada compatível com F008. Gravação do catálogo, do status do check e dos novos avisos deve ser atômica ou recuperável.
- **RF-028**: Na inicialização, a aplicação deve recuperar verificações interrompidas como interrompidas/falhas, preservar o último catálogo, não gerar avisos de resposta não confirmada e não disparar download. Se monitoramento permanecer habilitado, deve calcular a próxima execução sem tempestade de chamadas.
- **RF-029**: Notificações e verificações não podem criar `DownloadJob`, iniciar F005, alterar páginas/originais, exportar ou acionar F009. Download e envio continuam exigindo ações independentes e explícitas.
- **RF-030**: Logs e diagnósticos devem omitir segredos, credenciais, conteúdo de capítulos, URLs com parâmetros e payloads; falhas devem ser sanitizadas e mapeadas para mensagens acionáveis em português brasileiro.
- **RF-031**: Testes automatizados devem cobrir catálogo alterado, ID estável com metadado alterado, ID duplicado/conflictante, novos IDs, primeira linha de base, indisponibilidade, resposta parcial, Retry-After, respeito ao intervalo, concorrência, desativação, fechamento/reabertura, cancelamento, notificações, preservação do último catálogo e zero downloads/envios automáticos. Nenhum teste deve acessar fonte pública.
- **RF-032**: README e documentação de uso devem explicar atualização manual, monitoramento opt-in, intervalo efetivo e limites, estado de fonte sem autorização, notificações locais e diferença entre detectar capítulos, baixar e enviar.
- **RF-033**: Antes de habilitar qualquer fonte real, a equipe deve verificar documentação oficial, autorização para consultas de catálogo, limites, compatibilidade de comportamento e dependências conforme a constituição. Não se pode inferir APIs, frequência, parâmetros ou opções de CLI.

### Requisitos Não Funcionais

- **RNF-001**: A aplicação permanece compatível com Windows 10/11 e Python 3.12+, com interface e documentação para usuário em português brasileiro e símbolos de código em inglês.
- **RNF-002**: A interface deve responder a ações de navegação e cancelamento em até 200 ms durante verificações, medido no perfil de referência de F002.
- **RNF-003**: As rotinas de atualização devem ser determinísticas para as mesmas identidades e dados, idempotentes e limitadas pelas políticas declaradas do provedor.
- **RNF-004**: O último catálogo válido permanece consultável durante indisponibilidade e recuperação; dados parciais nunca substituem dados completos.
- **RNF-005**: Configuração, status, notificações e histórico permanecem locais; nenhum capítulo ou dado de biblioteca é enviado a terceiros além da consulta de metadados explicitamente autorizada à fonte.
- **RNF-006**: A rotina periódica não pode operar com o aplicativo fechado, ultrapassar o intervalo permitido ou manter conexões/tarefas sem estado observável e cancelável.
- **RNF-007**: Erros devem ser apresentáveis sem segredo, payload, URL privada ou exposição desnecessária de título/identidade em log.

### Entidades Principais

- **CatalogCheck**: Tentativa manual ou periódica por mangá/provedor, com início, fim, resultado, IDs contabilizados, estado de completude, próximo horário permitido e erro sanitizado.
- **ProviderScopedChapterId**: Identidade estável de capítulo no escopo do provedor e da obra; não depende de título, posição ou número de exibição.
- **ChapterWatchSettings**: Preferência explícita para monitorar um mangá, intervalo escolhido, última consulta e aviso local habilitado/silenciado.
- **ChapterUpdateNotice**: Aviso local vinculado a um mangá e a um conjunto de IDs novos, com data, estado lido/silenciado e deduplicação persistente.
- **ProviderCheckPolicy**: Capacidades, autorização de consulta, limite mínimo de intervalo, concorrência/cooldown e termos que autorizam ou bloqueiam atualizações.

## Critérios de Sucesso Mensuráveis

- **CS-001**: Em 100% das atualizações manuais com fixture válida, a lista exibida coincide com o conjunto de IDs recebido, mantém IDs locais e segue a ordenação de F004.
- **CS-002**: Em 100% das repetições do mesmo catálogo, são criados zero registros de capítulo duplicados e zero avisos repetidos.
- **CS-003**: Em 100% dos catálogos posteriores com IDs novos, cada ID elegível aparece uma vez e gera no máximo um aviso local por mangá; a linha de base inicial gera zero avisos de novidade.
- **CS-004**: Em 100% dos casos de indisponibilidade, resposta parcial, cancelamento ou estrutura inválida, o último catálogo completo e seus arquivos permanecem inalterados.
- **CS-005**: Em 100% dos testes com relógio simulado, nenhuma consulta periódica ocorre antes do intervalo escolhido e do limite mais restritivo declarado pela fonte.
- **CS-006**: Em 100% dos cenários de fonte indisponível, monitoramento desativado ou aplicativo fechado, não ocorre requisição de rede; após `Retry-After`, não ocorre consulta antes do horário permitido.
- **CS-007**: Em 10 ciclos de encerramento/reabertura, 100% das preferências, horários, avisos, IDs e resultados confirmados permanecem consistentes; nenhum `DownloadJob` ou envio é criado pela atualização.
- **CS-008**: Durante consulta simulada com atraso, todas as medições de resposta da interface permanecem em até 200 ms e cancelar/desativar não deixa atualização parcial visível.
- **CS-009**: A suíte automatizada realiza zero conexões externas e identifica claramente toda fixture como simulada.
- **CS-010**: Enquanto `B003-REAL-SOURCE` ou ausência de autorização de consulta estiver vigente, a aplicação apresenta zero fontes reais de atualização como habilitadas.

## Premissas

- A atualização aplica-se somente a mangás associados a provedor registrado em F003; o usuário não fornece um host arbitrário para consulta.
- Monitoramento periódico é uma preferência local, desligada por padrão, e só consulta mangás selecionados expressamente.
- O intervalo é uma preferência de produto, subordinada ao limite mais restritivo publicado/declarado pela fonte. Uma fonte sem limites necessários não recebe frequência inventada.
- A primeira listagem válida é a linha de base. Novidades passam a ser calculadas nas consultas completas seguintes.
- Somente identidade estável qualificada permite dizer que um capítulo é novo. Capítulos importados manualmente sem vínculo comprovável não são pareados por título ou número.
- Notificações F010 são locais dentro da aplicação e não dependem de serviço de push, nuvem ou notificação de terceiros.
- `docs/roadmap.md` não existe neste checkout. F010 foi sequenciada após F009, seguindo as specs anteriores e a descrição fornecida, sem inferir requisitos do roadmap ausente.
- F003 mantém `B003-REAL-SOURCE`: até haver fonte autorizada e capacidades verificadas para consulta, resultados de fixture servem somente aos testes/demonstrações identificados; a consulta real permanece bloqueada.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em `../../.specify/memory/constitution.md`: arquitetura por camadas, fontes autorizadas, limites, operação responsiva/cancelável, persistência local, migrações, recuperação, logs seguros, testes e documentação.
- F001 — Fundação: identidade e dados locais de mangás/capítulos, armazenamento e migrações iniciais.
- F002 — Interface desktop: Biblioteca, estados, teclado e responsividade em 200 ms.
- F003 — Provedores extensíveis: `MangaProvider`, capacidade `get_chapters`, erros tipados, validação do destino, autorização e `B003-REAL-SOURCE`.
- F004 — Catálogo e capítulos: IDs estáveis qualificados, reconciliação, ordenação numérica/especial e seleção preservada.
- F005 — Downloads: rate limit, Retry-After, erros e política de que consulta de catálogo não cria downloads.
- F008 — Biblioteca local: persistência/histórico, migração e recuperação de relações e estados de catálogo.
- A decisão de habilitar qualquer provedor real depende de evidência oficial específica de consulta de metadados e seus limites; a autorização de download de imagens não pode ser presumida a partir de autorização de API.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Uma consulta periódica ultrapassa os limites ou termos da fonte. | Exigir capacidades e limites documentados, intervalo efetivo mínimo, concorrência limitada e respeito a Retry-After; sem informação suficiente, desabilitar rotina real. |
| A ausência de IDs estáveis causa falso aviso ou duplicação. | Comparar somente ID estável qualificado; sem ID confiável, não notificar automaticamente. |
| Uma resposta parcial remove capítulos conhecidos ou sobrescreve o último catálogo. | Validar completude antes de commit e preservar atomicamente a última versão válida. |
| Uma fixture parece uma integração real. | Marcar como simulada em UI/testes e manter `B003-REAL-SOURCE` explícito. |
| Agenda gera rajada após suspensão, reinício ou retorno de rede. | Não acumular execuções perdidas; coalescer por mangá/provedor e limitar a uma verificação vencida por item. |
| Novo aviso dispara download ou envio sem consentimento. | Separar notificação, DownloadJob F005 e transferência F009; exigir ações próprias e nunca encadear automações. |
| Alteração de política da fonte torna frequência inválida. | Revalidar documentação e desativar capacidade quando autorização/limite deixa de estar confirmado. |
| Falha entre atualização e gravação deixa catálogo inconsistente. | Persistir lote completo e avisos de forma atômica ou recuperável e testar interrupções. |

### Fora do Escopo

- Download de capítulos, páginas ou imagens iniciado automaticamente, em segundo plano ou a partir de notificação.
- Envio SMTP/Send to Kindle, exportação ou qualquer transferência automática para dispositivo/terceiros.
- Fonte real, scraping genérico, integração com serviços sem autorização verificável, remoção de `B003-REAL-SOURCE` por esta especificação ou apresentação de fixtures como dados reais.
- Login, autenticação, CAPTCHA, DRM, paywall, conteúdo removido ou restrições de acesso contornadas.
- Serviço do Windows, execução com o aplicativo fechado, notificação push, serviço em nuvem ou sincronização entre dispositivos.
- Pareamento heurístico entre capítulos do provedor e capítulos importados localmente por nome, título, número ou semelhança de conteúdo.
- Exclusão física de capítulos, páginas, originais, derivados ou exportações quando a fonte remove um item.
- Histórico de leitura, acompanhamento de progresso de leitura ou garantia de que capítulo novo está completo/baixável.

### Estratégia de Verificação

Usar Pytest com provedor/transportes e relógio simulados, banco e diretórios temporários. Cobrir primeira linha de base, catálogo alterado, ID preservado com metadados alterados, novos IDs, duplicatas idênticas e conflitantes, capítulos especiais/decimais, resposta incompleta, indisponibilidade, timeout, Retry-After, limites, concorrência e restrição de capacidades. Testar monitoramento inicialmente desligado, ativação explícita, intervalo configurado e efetivo, desativação em cada etapa, fechamento/reabertura/suspensão e ausência de tempestade de consultas. Conferir cancelamento, atomicidade, migração, deduplicação de avisos, persistência lido/silenciado, preservação de arquivos e catálogo anterior, logs sanitizados e zero criação de DownloadJob/Export/TransferJob. Nenhum teste deve acessar fontes públicas ou a Internet.
