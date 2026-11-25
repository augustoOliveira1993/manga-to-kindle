# Especificação de Funcionalidade: F009 — Envio ao Kindle do Manga to Kindle

**Feature Branch**: `009-kindle-send`

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Após uma exportação local válida, oferecer abertura da pasta de saída e da página oficial Send to Kindle para envio manual. Opcionalmente permitir envio SMTP com configuração escolhida pela pessoa usuária, endereço Kindle e remetente autorizados, confirmação explícita para cada tentativa e credenciais guardadas no cofre do Windows. Informar aceitação pelo servidor sem alegar entrega ao dispositivo. Não automatizar login Amazon nem presumir uma API pública de envio.

## Histórias de Usuário e Testes

### História 1 — Abrir o fluxo manual do Send to Kindle (Prioridade: P1)

Como pessoa usuária, quero abrir a pasta que contém minha exportação e a página oficial Send to Kindle, para escolher e enviar manualmente um arquivo que revisei.

**Por que esta prioridade**: Este é o caminho padrão, não exige guardar credenciais nem transferir conteúdo sem uma ação explícita.

**Teste independente**: Com uma exportação EPUB válida e um lançador de sistema simulado, acionar a opção de envio manual e verificar a abertura da pasta correta e da página oficial, sem requisição de upload nem leitura automatizada da página.

**Cenários de aceitação**:

1. **Dado** um pacote exportado e íntegro, **quando** a pessoa usuária escolhe “Abrir no Send to Kindle”, **então** o aplicativo abre a pasta de saída e a página oficial no navegador padrão, deixando a seleção e o envio do arquivo sob controle da pessoa usuária.
2. **Dado** que o navegador ou a pasta não podem ser abertos, **quando** a ação é tentada, **então** o aplicativo informa qual abertura falhou e oferece o caminho local e o link para cópia ou abertura manual.
3. **Dado** um pacote ausente, alterado ou inválido, **quando** a pessoa usuária tenta abrir o fluxo, **então** o aplicativo sinaliza a divergência e não apresenta o arquivo como exportação válida.

### História 2 — Configurar envio SMTP opcional (Prioridade: P2)

Como pessoa usuária que prefere e-mail, quero cadastrar meu servidor SMTP, remetente e endereço Kindle, para enviar um arquivo exportado sem expor minha senha à aplicação ou a seus logs.

**Por que esta prioridade**: O envio direto pode reduzir etapas, mas exige configuração, consentimento para transferência e proteção de credenciais.

**Teste independente**: Usar um cofre de credenciais falso e um servidor SMTP simulado para validar gravação e recuperação da configuração, TLS, autenticação, destinatário e falhas sem contatar serviços públicos.

**Cenários de aceitação**:

1. **Dado** que SMTP não foi configurado, **quando** a pessoa usuária abre as opções de envio, **então** o fluxo manual continua disponível e nenhuma tentativa de rede ocorre.
2. **Dado** um perfil SMTP, **quando** a pessoa usuária salva a configuração, **então** os dados não secretos podem ser persistidos localmente e a senha só é gravada no cofre de credenciais do Windows; indisponibilidade do cofre não habilita armazenamento em texto simples.
3. **Dado** que o remetente não foi autorizado nas configurações da conta Kindle ou que o endereço Kindle não foi confirmado pela pessoa usuária, **quando** ela configura o perfil, **então** o aplicativo explica que não pode verificar a autorização na Amazon e não trata a configuração como validada.

### História 3 — Autorizar cada envio e entender seu resultado (Prioridade: P2)

Como pessoa usuária, quero revisar arquivo, destinatário e servidor antes de cada envio SMTP e saber se o servidor aceitou a mensagem, para autorizar cada transferência e não confundir aceitação com entrega.

**Por que esta prioridade**: A autorização deve cobrir o arquivo e o destino exatos em cada transferência; uma resposta SMTP não comprova que o Kindle recebeu ou processou o arquivo.

**Teste independente**: Com servidor simulado, tentar enviar sem confirmação, confirmar um EPUB, testar respostas de aceitação e rejeição e desconexão após os dados da mensagem; verificar que somente os resultados comprováveis aparecem no histórico.

**Cenários de aceitação**:

1. **Dado** um arquivo exportado e um perfil configurado, **quando** a pessoa usuária inicia um envio, **então** o diálogo apresenta arquivo, tamanho, destinatário, remetente, host SMTP, assunto e a informação de que o conteúdo sairá do dispositivo; a pessoa usuária confirma que o destinatário Kindle está correto/autorizado e que o remetente é permitido, e só a confirmação explícita dessa tentativa autoriza a submissão.
2. **Dado** que a pessoa usuária cancela o diálogo, **quando** o fluxo termina, **então** nenhum dado é transmitido e nenhum estado de aceitação é registrado.
3. **Dado** uma resposta final positiva do servidor após o envio da mensagem, **quando** o envio termina, **então** o estado é “Aceito pelo servidor SMTP — entrega ao Kindle não confirmada”; o aplicativo não apresenta “Entregue”.
4. **Dado** uma rejeição explícita antes da aceitação final, **quando** o servidor responde, **então** o estado indica falha/rejeição e apresenta uma ação segura; nova tentativa exige confirmação própria.
5. **Dado** que a conexão é interrompida após o início da transmissão e antes de uma resposta final conhecida, **quando** o aplicativo recupera o trabalho, **então** o estado é “Resultado desconhecido”, sem reenvio automático.

### História 4 — Consultar o histórico local de transferências (Prioridade: P3)

Como pessoa usuária, quero consultar o resultado e o horário das tentativas anteriores, para distinguir exportações locais de mensagens aceitas ou falhas de envio.

**Por que esta prioridade**: O registro local dá rastreabilidade sem replicar conteúdo nem sugerir estados que a aplicação não consegue observar.

**Teste independente**: Registrar tentativas simuladas aceitas, rejeitadas, canceladas e ambíguas; reiniciar o aplicativo e conferir estado, vínculo com a exportação e ausência de reenvio automático.

**Cenários de aceitação**:

1. **Dado** um histórico de tentativas, **quando** a pessoa usuária o consulta, **então** vê data, arquivo exportado, canal e resultado, com endereço de destino mascarado por padrão.
2. **Dado** um envio aceito pelo servidor, **quando** a pessoa usuária reabre o histórico, **então** a interface continua indicando que a entrega ao Kindle não foi confirmada.
3. **Dado** um aplicativo encerrado durante a transmissão, **quando** ele reinicia, **então** a tentativa fica como interrompida ou de resultado desconhecido conforme a etapa persistida e não é repetida automaticamente.

### Casos extremos

- A pasta de exportação foi movida, o arquivo foi apagado, alterado ou está aberto/bloqueado por outro processo.
- A pasta ou o link oficial não podem ser abertos pelo sistema operacional, navegador padrão ou política corporativa.
- O navegador abre sem sessão Amazon, pede autenticação, exibe CAPTCHA ou recusa o arquivo; qualquer interação continua manual.
- O arquivo foi exportado em formato não confirmado pela documentação atual para o canal escolhido; CBZ não é presumido compatível com Send to Kindle.
- O EPUB tem layout fixo, tamanho acima do limite vigente ou características que o serviço não converte como esperado.
- O perfil SMTP está incompleto, foi alterado depois da confirmação, ou o cofre não está disponível, bloqueado ou contém uma credencial removida.
- O host SMTP não resolve, está indisponível, apresenta certificado inválido, não oferece o modo TLS configurado, exige autenticação adicional ou rejeita as credenciais.
- O destinatário está malformado, não é o endereço pessoal Kindle correto ou não está associado à conta esperada.
- O remetente não foi incluído na lista autorizada de remetentes de documentos pessoais da conta Kindle.
- O servidor rejeita remetente/destinatário, tipo, tamanho ou quota; envia resposta temporária de limite; ou desconecta durante a transação.
- O limite de tamanho do servidor SMTP não é conhecido, não é anunciado ou difere do limite do Send to Kindle pelo navegador.
- A pessoa usuária cancela antes da transmissão, durante a transmissão ou após os dados terem sido enviados, mas antes da resposta final.
- A aplicação encerra, o computador suspende ou a rede cai antes, durante ou após o envio dos dados SMTP.
- O mesmo arquivo e destinatário já tiveram tentativa aceita; a pessoa usuária pode querer uma segunda cópia, mas a aplicação deve avisar sobre possível duplicata.
- A pessoa usuária escolhe repetição depois de um resultado ambíguo; o aplicativo não deve afirmar que a tentativa anterior falhou.
- A conta recebe uma notificação posterior de falha, mas o aplicativo não tem acesso autorizado à caixa postal para observá-la.
- O nome de arquivo, assunto, caminho ou resposta do servidor contém texto de livro, endereço pessoal, caracteres de controle ou dados que não podem ser gravados em logs sem sanitização.

## Requisitos

### Requisitos Funcionais

- **RF-001**: Após uma exportação concluída e validada por F007, a interface deve oferecer como ação principal o fluxo manual “Abrir no Send to Kindle”.
- **RF-002**: O fluxo manual deve abrir, somente após ação da pessoa usuária, a pasta exata da exportação e a página oficial `https://www.amazon.com/sendtokindle` no navegador padrão. A pessoa usuária seleciona e envia o arquivo manualmente.
- **RF-003**: Abrir a página oficial não deve carregar, selecionar, anexar ou enviar automaticamente o arquivo, iniciar login, preencher formulários, automatizar CAPTCHA ou ler estado da conta Amazon. A feature não presume API pública de envio.
- **RF-004**: Se a abertura de pasta ou página falhar, o aplicativo deve informar a falha separadamente e oferecer o caminho local e o link em texto para ação manual.
- **RF-005**: Antes de oferecer envio, o aplicativo deve confirmar que o artefato de F007 ainda existe e que sua identidade/checksum registrado corresponde aos bytes atuais. Arquivo ausente ou alterado deve bloquear SMTP e ser distinguido de falha de transferência.
- **RF-006**: O fluxo manual deve comunicar que os formatos, tamanho e comportamento de layout são definidos pelo serviço externo e podem mudar. A documentação atual da Amazon, consultada em 2026-11-25, lista EPUB entre os formatos e informa limite de até 200 MB por arquivo para o serviço Send to Kindle; esse valor deve ser revalidado antes da implementação/liberação e não pode ser tratado como limite SMTP.
- **RF-007**: O envio SMTP deve ser opcional e desativado até a pessoa usuária configurar explicitamente um perfil. Salvar o perfil não pode enviar mensagem nem abrir conexão de rede automaticamente.
- **RF-008**: O perfil deve identificar host e porta SMTP, modo de proteção TLS, endereço do remetente, nome de usuário se aplicável e exatamente um endereço de destino Kindle. A validação de conexão só pode ocorrer por ação explícita “Testar conexão”, que não transmite livro nem envia e-mail.
- **RF-009**: O aplicativo deve solicitar que a pessoa usuária confirme que o destino é o endereço Kindle correto e que o remetente está na lista autorizada de remetentes de documentos pessoais da conta. Como não há verificação da conta Amazon, a interface deve identificar isso como autodeclaração não verificada.
- **RF-010**: Senhas e segredos SMTP devem ser gravados exclusivamente no cofre de credenciais do Windows. Banco, arquivos de configuração, histórico, mensagens de erro e logs não podem armazenar segredo, nem mesmo como valor temporário persistido. Se o cofre falhar, não pode haver fallback em texto simples.
- **RF-011**: O transporte SMTP para a feature deve usar TLS com validação de certificado e identidade do host. Não pode haver downgrade silencioso, autenticação em canal sem TLS nem opção de ignorar certificado inválido. Os modos e requisitos aceitos devem ser verificados na documentação oficial da dependência escolhida antes da implementação.
- **RF-012**: A primeira versão do canal SMTP deve aceitar somente formatos de exportação cuja aceitação por e-mail para o endereço Kindle esteja confirmada na documentação oficial aplicável ao canal. A aceitação pela página web, isoladamente, não comprova suporte por SMTP. EPUB está listado para Send to Kindle nas referências verificadas; CBZ e AZW3 não devem ser presumidos aceitos. A lista deve ser revalidada e documentada antes de cada release relevante.
- **RF-013**: Cada operação SMTP deve tratar um artefato e um destinatário por vez. Envio em lote ou para múltiplos destinatários não pode ocorrer sem uma autorização individual para cada mensagem.
- **RF-014**: Antes de cada mensagem, inclusive repetição, a interface deve apresentar o arquivo exato e tamanho, checksum abreviado, destino, remetente, host e porta, assunto e um aviso claro de que o conteúdo sairá do dispositivo. Na mesma confirmação, a pessoa usuária deve afirmar que o destino é seu endereço Kindle correto/autorizado e que o remetente está autorizado; só então aquela tentativa pode começar.
- **RF-015**: Ao confirmar, a aplicação deve usar o pacote exportado por F007 como anexo sem modificar, recomprimir, dividir ou substituir silenciosamente o artefato. Uma transformação exigiria nova exportação identificada e uma nova confirmação.
- **RF-016**: O assunto e corpo padrão não devem adicionar conteúdo do livro além do nome de arquivo/anexo necessário ao envio. Se forem editáveis, os valores finais devem aparecer na confirmação antes de cada envio.
- **RF-017**: A aplicação deve verificar limites documentados/configurados do servidor SMTP e tamanho estimado da mensagem, inclusive a codificação do anexo quando aplicável. Se o limite for conhecido e excedido, deve bloquear antes da transmissão; se desconhecido, deve avisar que o servidor ou serviço pode recusar. Não deve aplicar ao SMTP o limite do canal web nem dividir a mensagem automaticamente.
- **RF-018**: Operações de teste e envio devem ocorrer fora da thread gráfica, apresentar estado/progresso por etapa quando disponível e permitir cancelamento enquanto interromper a operação for seguro.
- **RF-019**: A aplicação deve diferenciar, no mínimo, aguardando confirmação, enviando, cancelado antes da submissão, rejeitado/falha antes da aceitação, aceito pelo servidor SMTP e resultado desconhecido após transmissão sem resposta final.
- **RF-020**: Uma resposta final positiva SMTP após a mensagem ser transmitida deve ser descrita como “Aceito pelo servidor SMTP”. O texto “Entregue” não pode ser usado como resultado do Kindle sem evidência autoritativa independente de entrega no dispositivo/conta.
- **RF-021**: A aceitação SMTP não deve ser tratada como confirmação de ingestão, conversão, arquivamento ou entrega ao Kindle. A aplicação não deve monitorar caixa postal, notificação de bounce ou conta Amazon nesta feature.
- **RF-022**: Uma recusa final conhecida deve apresentar resultado de falha e causa sanitizada. Respostas temporárias (4xx) devem ser diferenciadas de rejeições permanentes (5xx); uma resposta temporária pode oferecer nova tentativa manual e respeitar instruções de espera documentadas pelo servidor/provedor, sem inventar intervalo nem repetir automaticamente. Toda repetição requer a confirmação do RF-014.
- **RF-023**: Se houver desconexão ou timeout após o fim dos dados da mensagem e antes da resposta final, o resultado deve ser “Desconhecido”. O aplicativo não deve reenviar automaticamente essa mensagem, pois o servidor pode tê-la aceitado.
- **RF-024**: Cancelar antes da transmissão deve impedir qualquer envio. Durante a transmissão, o aplicativo deve parar somente se puder fazê-lo sem reportar falsamente que o servidor não recebeu a mensagem; caso contrário, deve marcar o resultado como desconhecido.
- **RF-025**: TransferJob e histórico devem ser persistidos localmente com migração versionada, vínculo ao Export/ExportPackage, checksum, canal, timestamps, estado, confirmação e instantâneo do host, remetente e destinatário usado naquela tentativa. O destinatário deve aparecer mascarado no histórico por padrão. Credenciais, corpo/anexo e conteúdo de páginas não podem ser copiados para a base; erros persistidos devem ser sanitizados.
- **RF-026**: Na inicialização, trabalhos interrompidos devem ser reconciliados com a última etapa persistida. Estado ambíguo não pode ser convertido em falha certa ou aceitação certa, nem provocar repetição automática.
- **RF-027**: Repetir intencionalmente arquivo já aceito deve mostrar aviso de possível duplicata e exigir a confirmação completa de uma nova tentativa; a aplicação não deve bloquear reenvio deliberado nem criá-lo em segundo plano.
- **RF-028**: Logs e diagnósticos não devem incluir credenciais, tokens, conteúdo binário, corpo da mensagem, páginas, assunto com dados de livro, endereço de e-mail completo ou caminho absoluto sensível. Respostas SMTP e exceções devem ser sanitizadas antes do registro.
- **RF-029**: A tela e os diálogos devem permitir navegar, revisar destinatário e confirmar/cancelar por teclado, anunciar estados de envio e falha e manter os estados vazios, carregando, erro e sucesso alinhados ao padrão F002.
- **RF-030**: Testes automatizados devem usar servidor SMTP simulado local e cofre falso; não podem enviar mensagem para SMTP público, conta Amazon real ou dispositivo Kindle. Devem cobrir aceite, recusas, limite, autenticação, TLS, timeout, cancelamento, resultado ambíguo, reinício, confirmação e sanitização dos logs.
- **RF-031**: README e documentação de uso devem explicar o fluxo manual, o que a abertura do site faz/não faz, autorização de destinatário e remetente, guarda de credenciais, limites, estados de SMTP, ausência de confirmação de entrega, formatos testados e tratamento de falhas.
- **RF-032**: Antes de incluir dependências de envio SMTP ou cofre de credenciais, a equipe deve verificar documentação oficial, suporte à versão de Python e Windows suportados, APIs e licenças, resolver versões com `uv` e registrar as versões; nenhum método ou opção CLI pode ser inferido.
- **RF-033**: Ao substituir ou remover um perfil SMTP, a interface deve oferecer a remoção explícita da credencial associada do cofre do Windows e informar se a limpeza falhar; a credencial não pode ser copiada para um arquivo como forma de migração.

### Requisitos Não Funcionais

- **RNF-001**: A feature deve manter as plataformas e tecnologias do produto definidas na constituição: Windows 10/11, Python 3.12 ou superior e PySide6, com interface e documentação de usuário em português brasileiro.
- **RNF-002**: A interface deve permanecer responsiva durante abertura do sistema, verificação local, conexão e envio; em testes de interação, a resposta a eventos da janela não deve exceder 200 ms.
- **RNF-003**: Todos os efeitos externos de SMTP devem ocorrer após ação explícita e consentimento por tentativa. Nenhuma transferência pode ser disparada por exportação concluída, inicialização, retomada ou configuração salva.
- **RNF-004**: Segredos devem permanecer no cofre do sistema operacional; os testes devem demonstrar que um segredo sentinela não aparece na base, arquivos de configuração, logs ou mensagens de erro.
- **RNF-005**: Persistência da tentativa e reconciliação de arquivos devem sobreviver ao encerramento inesperado sem perder Export válido, duplicar envio automaticamente ou apresentar estado de entrega incorreto.
- **RNF-006**: Os testes de integração SMTP devem funcionar isolados, determinísticos e sem depender da Internet, da conta Amazon ou de credenciais reais.
- **RNF-007**: A aplicação deve apresentar uma ação possível para cada falha previsível, sem jargão SMTP desnecessário e sem apagar/exportar novamente o conteúdo como efeito colateral.

### Entidades Principais

- **Export / ExportPackage**: Resultado local de F007, arquivo, formato, destino, identidade, checksum e estado de validação; é a origem exata do anexo.
- **SmtpProfile**: Configuração de host, porta, TLS, remetente, referência ao segredo no cofre e um endereço Kindle informado pela pessoa usuária; nunca contém a senha.
- **TransferJob**: Tentativa individual, consentimento registrado, vínculo ao ExportPackage, tamanho/checksum, canal, etapa, estado, horário e resultado sanitizado.
- **TransferConsent**: Confirmação explícita relativa a um arquivo, destinatário e tentativa; não autoriza transferências futuras.
- **TransferOutcome**: Resultado observável do canal, distinguindo aceitação SMTP, rejeição, cancelamento e estado desconhecido; não equivale a entrega no Kindle.

## Critérios de Sucesso Mensuráveis

- **CS-001**: Em 100% dos testes do fluxo manual, o clique abre a pasta da exportação e a URL oficial configurada por referência verificável, sem transferir bytes do arquivo nem automatizar interação web.
- **CS-002**: Em 100% das tentativas simuladas, nenhuma mensagem é transmitida sem uma confirmação individual que corresponda ao arquivo e destinatário exibidos.
- **CS-003**: 100% das respostas finais positivas simuladas aparecem como aceitas pelo servidor, com entrega ao Kindle não confirmada; nenhum caso sem evidência é rotulado como entregue.
- **CS-004**: Em 100% dos testes de desconexão após transmissão sem resposta final, o trabalho é classificado como desconhecido e não é repetido automaticamente após reinicialização.
- **CS-005**: Um segredo sentinela tem zero ocorrências na base SQLite, arquivos de configuração, logs e mensagens de erro após configuração, envio aceito e envio falho.
- **CS-006**: 100% das recusas simuladas por autenticação, destinatário, tipo, limite, TLS ou resposta SMTP geram estado e ação de recuperação correspondentes, sem exibir dados secretos.
- **CS-007**: Em 10 ciclos de encerramento/reabertura com histórico local, 100% das tentativas mantêm identidade, vínculo ao pacote, horários e estado válido, sem novo envio de rede.
- **CS-008**: Durante teste de envio com atraso simulado, todas as medições de resposta da interface permanecem em até 200 ms e o cancelamento em etapa segura é percebido sem bloquear navegação.
- **CS-009**: Testes automatizados da feature fazem zero conexões externas; somente o servidor SMTP simulado local recebe mensagens de fixture.

## Premissas

- Uma exportação de F007 é a entrada do envio; F009 não baixa, transforma, converte nem corrige o conteúdo.
- O fluxo manual é o padrão e permanece disponível sem configurar SMTP ou guardar credenciais.
- O envio SMTP usa um endereço Kindle de documentos pessoais informado pela pessoa usuária. A Amazon exige que o endereço remetente esteja na lista de remetentes autorizados da conta; essa autorização é confirmada manualmente, pois F009 não consulta nem autentica a conta.
- A lista de tipos e limites do Send to Kindle pode mudar. Referências verificadas nesta especificação refletem a documentação consultada em 2026-11-25 e devem ser revistas antes da implementação/liberação.
- A aceitação do servidor SMTP prova somente que esse servidor aceitou responsabilidade pela mensagem conforme o protocolo. F009 não tem um canal de confirmação posterior da Amazon ou do Kindle.
- A pessoa usuária tem direito de transferir o material escolhido e confirma por tentativa que autoriza aquela saída do dispositivo.
- `docs/roadmap.md` não existe neste checkout. F009 segue F008 e os requisitos fornecidos nesta solicitação; a ordem de implementação preserva F001–F008 sem inferir conteúdo ausente do roadmap.

## Dependências

- Constituição em `../../.specify/memory/constitution.md`: autorização explícita para transferir, armazenamento local, migrações, operações recuperáveis, responsividade, logs sem segredos e documentação/testes por feature.
- F001 — Fundação: dados locais, inicialização/encerramento e contrato `Export`.
- F002 — Interface desktop: navegação, acessibilidade por teclado, estados e padrão de responsividade de 200 ms.
- F007 — Exportação EPUB e KCC: geração local, validação, artefatos, caminho, formato e checksum da entrada.
- F008 — Biblioteca local: persistência versionada de atividades, relações, migrações, histórico e recuperação após reinício.
- Referências oficiais do Send to Kindle, tipos de arquivo, remetentes autorizados, limites atuais e regras SMTP devem ser novamente verificadas no planejamento e antes da integração.
- Dependências Python para SMTP e cofre do Windows ainda não foram escolhidas; compatibilidade, APIs, licenças e versões resolvidas devem ser provadas conforme a constituição, sem pressupor opção CLI ou comportamento não documentado.

## Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| A pessoa usuária interpreta “enviado” como entregue ao Kindle. | Usar “Aceito pelo servidor SMTP — entrega ao Kindle não confirmada”; nunca inferir estado de dispositivo. |
| A conexão cai após o servidor aceitar a mensagem e antes da confirmação chegar ao aplicativo. | Persistir “Resultado desconhecido”, não repetir automaticamente e explicar o risco de duplicata antes de tentativa manual. |
| Um log ou erro contém senha, endereço ou título do livro. | Sanitizar antes do logger e testar segredo sentinela, endereço e texto de livro em cada fronteira de erro. |
| Servidor de saída ou serviço Kindle recusa por tipo, tamanho, quota ou remetente não autorizado. | Validar o que é conhecido, comunicar incerteza quando o limite não é publicado e oferecer o fluxo manual; nunca dividir ou converter silenciosamente. |
| Mudança no site, formatos ou limites Amazon invalida orientações. | Abrir somente o endereço oficial, não depender de scraping/API, registrar a fonte e revalidar conteúdo antes de liberar versão. |
| Senha SMTP não pode ser protegida pelo cofre ou TLS está mal configurado. | Bloquear a operação, não guardar senha em outro lugar, validar identidade TLS e oferecer o caminho manual. |
| O pacote foi alterado depois da exportação, ou uma repetição cria duplicata. | Conferir identidade/hash antes do envio, mostrar checksum, avisar sobre tentativa já aceita e confirmar cada repetição. |
| Persistência registra estado positivo antes de a submissão ser comprovada. | Gravar transições de etapa recuperáveis; resultado final só após resposta positiva conhecida; reconciliar ambiguidades na inicialização. |

## Fora do Escopo

- Login Amazon automatizado, leitura de sessão/cookies, preenchimento de páginas, automação de CAPTCHA, scraping, API privada ou API pública de envio presumida.
- Upload automático do fluxo de navegador, envio ao concluir exportação, reenvio automático após falha/reinício ou envio em lote sem confirmação individual.
- Verificação de que um endereço, remetente ou dispositivo está registrado na conta Amazon; isso permanece confirmação manual da pessoa usuária.
- Leitura da caixa postal, processamento de bounce/DSN, confirmação de ingestão, conversão, sincronização ou entrega no Kindle.
- Configuração automática de provedores SMTP, descoberta de credenciais, OAuth presumido ou senha armazenada em texto simples.
- Conversão ou recompressão para contornar limites, divisão automática de anexo, envio de CBZ sem suporte confirmado ou garantia de layout fixo/qualidade de renderização.
- Envio via USB, descoberta de dispositivo conectado ou gerenciamento de conteúdo no Kindle.
- Sincronização de arquivos, metadados ou credenciais com nuvem, telemetria ou serviço de terceiros além do SMTP explicitamente autorizado.

## Estratégia de Verificação

Usar Pytest com fixtures locais e um servidor SMTP simulado. Cobrir autorização antes de cada envio, arquivo e checksum, cofre falso, TLS válido/inválido, autenticação, destinatário/remetente, resposta positiva final, rejeições temporárias/permanentes, limites conhecidos/desconhecidos, cancelamento, timeout, desconexão após os dados, estado ambíguo, repetição manual e retomada após reinício. Inspecionar base, configuração, logs e mensagens de erro com segredo sentinela e dados de fixture. Substituir lançadores de navegador e pasta por adaptadores simulados nos testes; executar uma verificação manual em Windows 10/11 da abertura do endereço/pasta e do fluxo de teclado. Nenhum teste automatizado deve acessar a Internet, conta Amazon ou servidor SMTP público; nenhum teste manual deve afirmar entrega ao Kindle sem confirmação independente.

## Referências Verificadas

- Amazon, [Send to Kindle](https://www.amazon.com/sendtokindle) — página oficial aberta somente por ação manual da pessoa usuária.
- Amazon, [Add an Email Address to Receive Documents in Your Kindle Library](https://digprjsurvey.amazon.com/csad/help/node/GX9XLEVV8G4DB28H?searchNodes=GDRLC59WEFZTBPU7&theme=light) — somente remetentes adicionados à lista de e-mails autorizados podem enviar documentos pessoais à biblioteca Kindle.
- Amazon, [Kindle Personal Document File Types That Support Notes](https://digprjsurvey.amazon.com/csad/help/node/TNtSm13k3txFI4EvDV) — inclui EPUB entre os tipos listados para documentos importados com Send to Kindle; esta referência não certifica layout fixo.
- Amazon, [Connect, Browse, and Transfer Files on E-Reader](https://digprjsurvey.amazon.com/csad/help/node/TCUBEdEkbIhK07ysFu) — documentação consultada informa até 200 MB por arquivo no serviço Send to Kindle e lista EPUB entre formatos; limite deve ser revalidado e não se aplica automaticamente ao SMTP configurado.
- IETF, [RFC 5321 — Simple Mail Transfer Protocol](https://www.rfc-editor.org/info/rfc5321/) — a resposta positiva final após os dados indica aceitação pelo servidor SMTP, que assume responsabilidade de entrega/relay; falhas posteriores não equivalem à confirmação do dispositivo pelo aplicativo.
- IETF, [RFC 3207 — SMTP Service Extension for Secure SMTP over TLS](https://www.rfc-editor.org/info/rfc3207/) — referência para STARTTLS e negociação de TLS em SMTP.
