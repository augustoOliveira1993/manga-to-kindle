# Especificação de Funcionalidade: F005 — Downloads do Manga to Kindle

**Feature Branch**: 005-download-queue

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Especificar fila persistente de downloads com concorrência limitada, timeout, retry com backoff e respeito a Retry-After, pausa, cancelamento e retomada segura. Validar tipo, tamanho e decodificação das imagens; gravar temporários e finalizar atomicamente; preservar ordem, detectar duplicatas e exibir progresso. Sem contornar bloqueios.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Enfileirar e acompanhar capítulos (Prioridade: P1)

Como pessoa usuária, quero iniciar o download autorizado dos capítulos selecionados e acompanhar páginas e capítulos, para saber o que está em andamento e o que foi concluído.

**Por que esta prioridade**: A fila e o progresso são o fluxo principal de aquisição local de páginas.

**Teste independente**: Selecionar capítulos em uma fixture de teste com transporte isolado, enfileirar o trabalho e conferir estados, limites de concorrência, progresso e ordem final das páginas.

**Cenários de aceitação**:

1. **Dado** um capítulo selecionado e uma fonte cujo uso para download está autorizado e declarado, **quando** a pessoa usuária inicia o trabalho, **então** o aplicativo cria um trabalho persistente e apresenta seu estado e progresso.
2. **Dado** que a fonte não declara capacidade ou autorização comprovável, **quando** a pessoa usuária tenta baixar, **então** a ação é bloqueada antes de qualquer conexão e a interface explica a limitação.
3. **Dado** que páginas terminam fora da ordem de leitura devido à concorrência, **quando** o capítulo é apresentado como concluído, **então** as páginas mantêm a ordem e as posições fornecidas pelo catálogo.
4. **Dado** um trabalho com mais de um capítulo, **quando** páginas são processadas, **então** o progresso é visível por página e capítulo e o total da fila não é confundido com o total de bytes.

### História 2 — Controlar, pausar e cancelar trabalhos (Prioridade: P1)

Como pessoa usuária, quero pausar, retomar ou cancelar um trabalho, para controlar o uso da conexão e interromper uma seleção sem perder arquivos válidos já concluídos.

**Por que esta prioridade**: Uma fila longa precisa permanecer sob controle e responder a interrupções sem corromper o catálogo ou os arquivos.

**Teste independente**: Pausar uma fila em execução, retomá-la, cancelar outra e interromper uma terceira durante o encerramento; verificar transições persistidas, arquivos temporários e páginas já finalizadas.

**Cenários de aceitação**:

1. **Dado** um trabalho em execução, **quando** a pessoa usuária o pausa, **então** nenhum novo pedido começa e a página atual termina ou pausa em um ponto seguro; o estado pausado permanece após reinício.
2. **Dado** um trabalho pausado, **quando** a pessoa usuária escolhe retomar, **então** páginas validadas não são baixadas outra vez e a execução continua em uma fronteira segura.
3. **Dado** um trabalho em execução, **quando** a pessoa usuária o cancela, **então** novas requisições cessam, arquivos temporários daquele trabalho são removidos e páginas já concluídas permanecem intactas.
4. **Dado** um trabalho que foi interrompido por encerramento inesperado, **quando** o aplicativo é aberto, **então** o trabalho aparece como interrompido e não inicia tráfego automaticamente; a retomada depende de ação explícita da pessoa usuária.
5. **Dado** que a fonte não suporta retomada segura de bytes, **quando** uma página incompleta é retomada, **então** seu temporário é descartado e a página recomeça do início, sem repetir páginas completas.

### História 3 — Recuperar falhas sem guardar arquivos inválidos (Prioridade: P1)

Como pessoa usuária, quero que falhas transitórias sejam tratadas com espera e que respostas inválidas sejam descartadas, para não receber arquivos truncados, corrompidos ou fora dos limites.

**Por que esta prioridade**: Repetições agressivas podem exceder limites da fonte, e arquivos incompletos ou malformados não podem entrar na biblioteca.

**Teste independente**: Usar um transporte de teste com timeouts, falhas transitórias, respostas HTTP 429/503, cabeçalho Retry-After, MIME incorreto, conteúdo excessivo, imagem corrompida e interrupção entre gravação e finalização; conferir política de retry e recuperação.

**Cenários de aceitação**:

1. **Dado** um erro transitório elegível para repetição, **quando** ocorre uma falha, **então** o trabalho espera segundo backoff limitado e tenta novamente até o máximo definido.
2. **Dado** uma resposta elegível com Retry-After, **quando** o cabeçalho contém duração ou data válida, **então** nenhuma nova tentativa ocorre antes do instante indicado; o prazo permanece salvo durante reinício.
3. **Dado** uma resposta que excede tipo, tamanho ou decodificação permitidos, **quando** a página é validada, **então** o temporário é descartado, a página não é registrada como concluída e a causa fica visível sem conteúdo sensível.
4. **Dado** que o processo termina entre a gravação temporária e a conclusão, **quando** o aplicativo reinicia, **então** a recuperação identifica o temporário órfão e mantém o último arquivo final íntegro.

### Casos extremos

- A fonte ou provedor não possui capacidade de download autorizada, autorização verificável, limite documentado ou destino aprovado.
- O usuário tenta baixar uma seleção vazia, repete um trabalho ativo ou seleciona capítulo já concluído.
- O provedor retorna páginas sem ID, com IDs duplicados, posição duplicada ou referência inconsistente.
- A conexão demora, para de entregar bytes, é interrompida ou retorna timeout após alguns bytes.
- O status HTTP é 401, 403, 404, 408, 429, 5xx, redirecionamento não declarado ou erro de limite.
- Retry-After está ausente, malformado, no passado, em formato de segundos ou data, ou posterior ao tempo em que o aplicativo será fechado.
- Content-Length está ausente, incorreto, excede o limite ou muda durante a leitura.
- MIME declarado não é permitido, não corresponde à assinatura ou o conteúdo não pode ser decodificado como imagem.
- A imagem tem tamanho comprimido válido, mas dimensões decodificadas excedem o limite de segurança.
- O disco fica sem espaço, perde permissão, falha durante gravação, renomeação ou persistência do banco.
- Dois trabalhos tentam gravar a mesma identidade de página ou a fonte retorna os mesmos bytes sob IDs distintos.
- A aplicação fecha durante fila ativa, espera de retry, pausa ou validação.
- A fonte suporta retomada de bytes, mas não fornece validador estável; ou anuncia suporte e responde com conteúdo incompatível.
- A atualização da lista de capítulos remove ou reordena páginas depois de um trabalho já persistido.
- Uma URL de redirecionamento aponta para host não aprovado, endereço privado ou destino com esquema rebaixado.
- Uma fonte exige login, CAPTCHA, DRM, pagamento ou apresenta bloqueio de acesso.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A área Downloads deve permitir enfileirar capítulos selecionados na F004 somente depois de validar a fonte, sua capacidade de download e a autorização aplicável definidas em F003.
- **RF-002**: Sem autorização verificável, documentação de uso local, limites e destinos permitidos, o trabalho deve ser recusado antes de abrir conexão. O provedor de fixtures de F003 não autoriza download remoto e não pode ser apresentado como fonte real funcional.
- **RF-003**: A fila deve persistir trabalhos, capítulos, páginas, tentativas, ordem original, estado, progresso conhecido e horário da próxima tentativa. Uma reinicialização não pode duplicar registros nem perder páginas concluídas.
- **RF-004**: O sistema deve limitar a no máximo duas transferências de página simultâneas globalmente. Um limite mais restritivo declarado pela fonte prevalece; limites de taxa e janelas de requisição documentados também devem ser respeitados.
- **RF-005**: Cada transferência deve possuir timeout finito de conexão, com padrão de 10 segundos, e timeout de inatividade de leitura, com padrão de 30 segundos sem novos bytes. A fonte pode exigir valores menores; uma política não pode ampliar limites da fonte.
- **RF-006**: Falhas transitórias de conexão e respostas HTTP 408, 429 e 5xx podem ser repetidas, com no máximo três tentativas adicionais após a tentativa inicial. O backoff padrão cresce em 1, 2 e 4 segundos e é limitado a 60 segundos; o trabalho permanece persistido durante a espera.
- **RF-007**: Para resposta elegível que inclua Retry-After válido como segundos ou data HTTP, a tentativa seguinte não pode ocorrer antes do prazo indicado. Esse prazo não pode ser reduzido pelo limite do backoff; uma data expirada ou cabeçalho inválido usa o backoff padrão. Tentativas automáticas cessam ao alcançar o máximo.
- **RF-008**: Respostas de autenticação/restrição, conteúdo ausente, tipo inválido, tamanho excedido, redirecionamento/destino recusado e conteúdo corrompido não devem ser repetidos automaticamente. O sistema não pode contornar autenticação, CAPTCHA, DRM, pagamento, 403 ou outra restrição.
- **RF-009**: O fluxo deve oferecer pausar, retomar e cancelar por trabalho. Pausar impede o início de novas páginas e conclui a página em andamento ou a interrompe em ponto seguro; cancelar encerra novas requisições e não remove páginas completas.
- **RF-010**: Trabalhos incompletos devem ser persistidos no encerramento seguro. Após encerramento inesperado, trabalhos em execução devem aparecer como interrompidos e exigir ação explícita de retomada, sem início automático de rede.
- **RF-011**: A retomada por página deve pular páginas concluídas e validadas. Retomada de bytes parciais só pode ocorrer quando a fonte declarar suporte e houver identidade/validador estável compatível; caso contrário, o temporário daquela página deve ser descartado e baixado novamente do início.
- **RF-012**: Cada página recebida deve respeitar os tipos raster permitidos JPEG, PNG ou WebP, com MIME declarado permitido, assinatura compatível e decodificação completa bem-sucedida. Tipos ativos ou desconhecidos, incluindo SVG, devem ser recusados.
- **RF-013**: Cada página deve ter no máximo 25 MiB comprimidos e 50 megapixels decodificados. O limite de bytes deve ser aplicado durante a leitura mesmo sem Content-Length confiável; o limite de pixels deve ser conferido antes de aceitar a imagem.
- **RF-014**: Os bytes originais recebidos devem ser preservados sem transformação. A gravação deve usar temporário dentro da área gerenciada pelo aplicativo, validar conteúdo e finalizar atomicamente sem sobrescrever arquivos originais ou arquivos de identidade diferente.
- **RF-015**: A persistência conjunta de arquivo e metadados deve ser recuperável. Na inicialização, a recuperação deve reconciliar temporários e arquivos finais com trabalhos/páginas persistidos; só pode remover temporário reconhecidamente pertencente ao aplicativo e a trabalho incompleto.
- **RF-016**: A identidade da página deve ser qualificada pela fonte e não depender da ordem de conclusão. Páginas repetidas com o mesmo ID dentro de um capítulo invalidam a resposta antes da persistência parcial.
- **RF-017**: Se o mesmo ID estável de página já tiver arquivo final validado, o sistema deve reutilizá-lo sem novo download. Conteúdo idêntico sob IDs distintos deve ser detectado por checksum e informado, mas cada identidade e posição devem ser preservadas; não remover páginas automaticamente.
- **RF-018**: Repetição de um trabalho ativo com a mesma fonte, capítulo e seleção de páginas deve ser reconhecida e não deve criar downloads concorrentes duplicados.
- **RF-019**: O progresso deve mostrar página atual, páginas concluídas/total conhecido e estado por capítulo e trabalho. Conclusões fora de ordem de rede devem continuar refletindo a ordem de leitura da F004. Totais desconhecidos não podem ser apresentados como percentuais exatos.
- **RF-020**: Falhas devem ser tipadas e apresentadas em português brasileiro com próxima ação possível. Logs não devem conter URL completa, query, credenciais, cabeçalho, corpo da resposta ou conteúdo de livro.
- **RF-021**: I/O, validação e decodificação não podem bloquear a thread gráfica. Trabalho interrompível deve responder a cancelamento com segurança e emitir progresso útil por página/capítulo.
- **RF-022**: Estados e resultados de DownloadJob devem respeitar as transições de F001. Pausado, em retry ou interrompido são não terminais; concluído, cancelado e falha definitiva não retornam a execução. Uma tentativa manual após falha definitiva cria um novo trabalho.
- **RF-023**: A fila e os resultados de página devem usar migrações locais versionadas, operações atômicas ou recuperação documentada. A falha de uma migração deve preservar o banco anterior e permitir diagnóstico sem segredo.
- **RF-024**: Testes automatizados devem simular transporte, relógio, falhas HTTP, Retry-After, interrupção de processo, encerramento, corrupção, limites de bytes/pixels, duplicatas, concorrência, recuperação de arquivos e ausência de tráfego real.
- **RF-025**: A documentação e o README devem explicar fila, controles, limites de imagem, retomada, retry e o estado bloqueado de fontes reais. A interface deve indicar quando nenhum provedor autorizado está habilitado.
- **RF-026**: A feature não pode enviar arquivos ou livros a Kindle, e-mail, nuvem ou terceiros; não pode alterar imagens originais nem realizar conversão de páginas.

### Requisitos Não Funcionais

- **RNF-001**: Interface e documentação voltadas à pessoa usuária devem estar em português brasileiro; identificadores de domínio, contratos e código permanecem em inglês.
- **RNF-002**: A interface deve responder a navegação, pausa e cancelamento em até 200 ms no perfil de referência F002, mesmo com duas transferências ativas.
- **RNF-003**: O uso de memória durante a recepção deve permanecer limitado pelo processamento em fluxo e limites de tamanho; não se deve carregar respostas sem limite na memória.
- **RNF-004**: A ordem final das páginas deve ser idêntica à ordem canônica F004 em 100% dos testes, independentemente da ordem e concorrência de conclusão.
- **RNF-005**: Arquivos de origem concluídos são imutáveis. Arquivos temporários incompletos nunca podem aparecer como páginas concluídas nem substituir silenciosamente um arquivo válido.
- **RNF-006**: A fila e os dados ficam no dispositivo local; logs são sanitizados; nenhum conteúdo de livro é enviado sem autorização específica e explícita.
- **RNF-007**: Os mesmos resultados de transporte e o mesmo relógio simulado devem produzir as mesmas decisões de retry, prazo, estado e recuperação.
- **RNF-008**: Todas as verificações de URL, DNS, destinos, redirecionamentos e capacidade continuam sujeitas às regras fail-closed de F003.

### Entidades Principais

- **DownloadJob**: Contrato de F001 estendido com origem, seleção estável, política de tentativas, estado persistente, progresso, timestamps e resultados por capítulo/página.
- **DownloadPageResult**: Identidade estável da página, posição canônica, estado de transferência, tentativas, tamanho, checksum e referência local final quando validada.
- **RetrySchedule**: Tentativa futura permitida e horário mínimo da próxima execução, incluindo prazo de Retry-After persistido.
- **Page**: Contrato local de F001, criado somente depois de bytes integralmente validados; aponta para o arquivo original imutável.
- **Arquivo temporário de trabalho**: Conteúdo parcial isolado, associado a trabalho e página; não é uma Page disponível para conversão nem uso posterior.
- **Capability de download**: Declaração verificável do provedor sobre autorização, limites, formatos, destinos e suporte a retomada; ausência ou dúvida bloqueia a operação.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: Em todos os testes, nunca há mais de duas páginas em transferência simultânea, e a concorrência é reduzida quando o limite documentado da fonte for menor.
- **CS-002**: Todas as tentativas respeitam o timeout configurado; nenhuma repetição acontece antes de Retry-After válido e nenhuma execução automática excede três tentativas adicionais.
- **CS-003**: 100% dos testes de pausa, cancelamento e reinício mantêm páginas completas, descartam ou retomam com segurança os parciais e não iniciam tráfego no reinício sem ação explícita.
- **CS-004**: 100% das imagens fora dos limites de MIME, assinatura, tamanho, pixels ou decodificação são recusadas sem substituir arquivos válidos nem registrar Page concluída.
- **CS-005**: Após interrupção simulada em cada fronteira de escrita/renomeação/persistência, a recuperação deixa o catálogo consistente e não altera imagens originais.
- **CS-006**: 100% dos capítulos concluídos preservam ordem e IDs estáveis; páginas duplicadas pelo mesmo ID não geram segundo arquivo, e bytes duplicados sob IDs distintos são detectados sem remover identidades.
- **CS-007**: Nos testes de conexão, não há requisições reais; nenhuma fonte sem autorização verificável inicia conexão.
- **CS-008**: Interface e controles de progresso, pausa e cancelamento respondem em até 200 ms no perfil de referência F002.

## Premissas

- F003 continua sem fonte real autorizada para download; o bloqueio B003-REAL-SOURCE permanece ativo.
- Até remover esse bloqueio, respostas HTTP, conteúdo binário e falhas são exercitados somente com transporte, relógio e provedor falsos de teste. Nenhum provedor falso é distribuído como se fosse real.
- O fluxo de produção só inicia quando uma fonte tiver autorização verificável para download local, documentação dos destinos e limites, atribuição/remoção e capacidade registrada no provedor.
- O aplicativo usa dois pedidos simultâneos como teto global padrão, timeout de conexão de 10 segundos, timeout de inatividade de leitura de 30 segundos, até três retries adicionais e limite de 60 segundos para backoff próprio; Retry-After nunca é reduzido para caber nesse teto.
- Limites padrão de imagem são 25 MiB comprimidos e 50 megapixels decodificados. Um limite menor do provedor ou da política local prevalece.
- Formatos suportados nesta feature são JPEG, PNG e WebP; o formato original é guardado sem recompressão ou transformação.
- Pausa/cancelamento não apagam páginas previamente concluídas; tentativa após falha definitiva é um novo DownloadJob, conforme estados terminais F001.
- A ausência de docs/roadmap.md foi confirmada; dependências são derivadas da sequência documentada F001–F004, sem presumir dependências de F006–F012.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em ../../.specify/memory/constitution.md: I/O fora da thread gráfica, cancelamento, progresso, persistência local, migrações, atomicidade, recuperação, privacidade e autorização.
- F001 — Fundação do Manga to Kindle: DownloadJob, Page, SQLite local, diretórios do usuário, migrações, logs sanitizados e encerramento seguro.
- F002 — Interface desktop do Manga to Kindle: área Downloads, seleção de perfil visual, acessibilidade e responsividade.
- F003 — Provedores extensíveis do Manga to Kindle: referências de página, capacidades, autorização, limites, erros tipados, validação de destino e bloqueio B003-REAL-SOURCE.
- F004 — Catálogo e capítulos do Manga to Kindle: IDs, ordenação canônica, seleção estável e capítulos selecionados que originam o trabalho.
- Não foi encontrado docs/roadmap.md; nenhuma dependência posterior é presumida.

### Bloqueio de Fonte Real

- **B003-REAL-SOURCE** continua vigente. Nenhuma fonte foi aprovada para baixar os capítulos e páginas pretendidos ao uso local. F005 especifica e testa a orquestração, persistência, validação e recuperação com transporte isolado; não declara download real funcional nem habilita tráfego remoto. A habilitação futura depende de evidência oficial e revisão explícita das permissões e limites.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Retry agressivo viola limite da fonte ou ignora Retry-After. | Repetir somente falhas transitórias, persistir o prazo mínimo, limitar tentativas e reduzir concorrência ao limite declarado. |
| Arquivo interrompido parece completo ou substitui imagem existente. | Validar bytes antes de finalizar, usar temporários próprios e finalização atômica com recuperação após crash. |
| Tipo ou imagem maliciosa consome memória/CPU. | Limites de tamanho e pixels, allowlist raster, conferência de assinatura e decodificação integral em trabalho de fundo. |
| Concorrência altera ordem das páginas. | Persistir posição do catálogo e separar ordem de leitura da ordem de conclusão. |
| Retomada parcial mistura representações de conteúdo. | Exigir capacidade explícita e validador estável; sem eles, descartar o parcial e reiniciar a página. |
| Cópia de arquivo excede área local ou substitui arquivo do usuário. | Gravar somente na área gerenciada, verificar pertencimento e não seguir caminhos fornecidos pela fonte como destinos locais. |
| Logs revelam URL, cabeçalhos ou conteúdo. | Registrar categorias de erro e IDs internos sanitizados, sem URL completa, corpos ou segredos. |
| Fixture induz impressão de integração funcional. | Sinalizar que testes são simulados e manter B003-REAL-SOURCE como bloqueio de produção. |

### Fora do Escopo

- Provedor real, tráfego HTTP de produção ou remoção do bloqueio B003-REAL-SOURCE sem autorização verificável.
- Contornar DRM, CAPTCHA, login, paywall, 401/403 ou qualquer restrição; usar cookies ou credenciais para contornar bloqueios.
- Conversão, recompressão, redimensionamento, edição ou substituição de imagem original.
- Criação de arquivos Kindle, transferência por USB/e-mail/nuvem, envio de livro ou integração com dispositivo.
- Busca/instalação de provedores externos ou scraping genérico de páginas.
- Especificar API de biblioteca de rede, opções CLI, nomes de classes de infraestrutura ou dependência de imagem ainda não validada nas versões oficiais/resolvidas do projeto.

### Estratégia de Verificação

Usar testes unitários de domínio para transições, ordenação, duplicatas e política de retry; testes de aplicação com transporte e relógio simulados para concorrência, falhas HTTP e Retry-After; testes de integração para fila SQLite, migração, temporários, atomicidade e recuperação; e testes da apresentação para progresso, pausa, cancelamento e responsividade. A suíte deve incluir matriz de falhas em cada fronteira de gravação, imagens válidas/corrompidas e limites imediatamente abaixo, no limite e acima. Nenhum teste desta feature deve acessar a internet.
