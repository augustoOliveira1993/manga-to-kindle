# Especificação de Funcionalidade: F007 — Exportação EPUB e KCC do Manga to Kindle

**Feature Branch**: 007-epub-kcc-export

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Exportar páginas ilustradas como EPUB com metadados, capa, sumário, ordem e direção configurável; permitir saída por capítulo ou volume, divisão por tamanho e CBZ opcional. Gerar EPUB 3 nativamente com serialização XML e ZIP da biblioteca padrão Python, sem biblioteca EPUB de terceiros. Oferecer adaptador opcional para KCC CLI somente com versão/opções verificadas na instalação real. Validar estrutura e testar manualmente em Kindle real; não prometer compatibilidade de layout fixo com Send to Kindle sem evidência. Considerar alternativa local compatível com USB somente se o conversor suportar e validar o formato.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Exportar EPUB organizado para leitura (Prioridade: P1)

Como pessoa usuária, quero exportar capítulos ou volumes com capa, metadados, sumário e direção de leitura configurável, para ler uma cópia local das páginas em um leitor compatível.

**Por que esta prioridade**: EPUB é o formato de saída principal e precisa manter identificação, ordem e navegação antes de oferecer conversores opcionais.

**Teste independente**: Exportar uma fixture com vários capítulos, páginas, capa e metadados; verificar o pacote EPUB, o sumário, a ordem do spine, a direção, os arquivos e a ausência de qualquer transferência.

**Cenários de aceitação**:

1. **Dado** capítulos com páginas processadas e selecionadas, **quando** a pessoa usuária escolhe um EPUB por capítulo, **então** é criado um EPUB independente por capítulo e cada um contém apenas suas páginas em ordem de leitura.
2. **Dado** capítulos com volume explícito, **quando** a pessoa usuária escolhe agrupamento por volume, **então** é criado um EPUB para cada volume e o sumário permite navegar para cada capítulo nele incluído.
3. **Dado** a direção direita-para-esquerda ou esquerda-para-direita escolhida, **quando** o EPUB é aberto, **então** a direção declarada corresponde à escolha e a sequência de páginas permanece a confirmada em F006.
4. **Dado** que autor ou capa não foram fornecidos, **quando** o pacote é criado, **então** nenhum autor é inventado e a capa é uma página tipográfica neutra baseada somente no título, claramente identificada como gerada.

### História 2 — Escolher divisão e formato opcional (Prioridade: P2)

Como pessoa usuária, quero dividir resultados acima de um tamanho escolhido e opcionalmente gerar CBZ, para controlar o tamanho dos arquivos mantendo páginas e capítulos completos.

**Por que esta prioridade**: Volumes e seleções grandes podem exceder limites definidos pela pessoa usuária ou pela ferramenta, mas a divisão não pode omitir nem reordenar páginas.

**Teste independente**: Exportar uma fixture acima do limite definido e conferir partes numeradas; exportar a mesma seleção em CBZ e comparar identidade e ordem das imagens.

**Cenários de aceitação**:

1. **Dado** um limite de tamanho configurado, **quando** o pacote ultrapassa esse limite, **então** a aplicação cria partes sequenciais somente em fronteiras de capítulo ou página e preserva toda a seleção.
2. **Dado** que um único capítulo excede o limite, **quando** a divisão está habilitada, **então** ele é dividido entre páginas; nenhuma página é fragmentada ou perdida.
3. **Dado** que uma única página não cabe no limite, **quando** a divisão é tentada, **então** o aplicativo não trunca o conteúdo e solicita um limite maior ou a desativação da divisão.
4. **Dado** a opção CBZ habilitada, **quando** a exportação termina, **então** o pacote contém as páginas processadas com nomes que preservam sua sequência; a interface avisa que leitores CBZ determinam sua própria direção de navegação.

### História 3 — Usar KCC quando compatível ou EPUB nativo (Prioridade: P2)

Como pessoa usuária, quero usar uma instalação compatível do KCC ou escolher o EPUB nativo, para obter a saída que funciona no meu fluxo sem depender de um conversor indisponível.

**Por que esta prioridade**: KCC pode oferecer formatos de leitor e fluxos adicionais, mas precisa ser opcional, verificável e não pode tornar a exportação EPUB dependente dele.

**Teste independente**: Simular binários KCC ausente, compatível, com argumentos diferentes, sem opção necessária, com timeout e com saída inválida; conferir o fallback nativo, isolamento do subprocesso, cancelamento e relatório. A etapa final de aceitação compara a saída em um Kindle físico e registra o modelo e a rota testados.

**Cenários de aceitação**:

1. **Dado** KCC não instalado, **quando** a pessoa usuária inicia a exportação, **então** o EPUB nativo permanece disponível e nenhuma instalação é baixada automaticamente.
2. **Dado** uma instalação detectada, **quando** o aplicativo verifica capacidades, **então** apresenta somente formatos e opções confirmados para aquela versão.
3. **Dado** uma opção requerida ausente, formato incompatível, risco de conexão não autorizado ou falha do KCC, **quando** a pessoa usuária tenta conversão externa, **então** o adaptador não executa argumentos adivinhados e oferece EPUB nativo se ainda viável.
4. **Dado** o EPUB de layout fixo finalizado, **quando** a equipe valida compatibilidade, **então** o resultado só é anunciado como testado para a combinação de arquivo, dispositivo, firmware e rota realmente ensaiada.

### Casos extremos

- Mangá sem título, seleção vazia, página original/derivada ausente ou uma página não processada para o perfil escolhido.
- Autor, capa, idioma ou volume ausentes; nome de capítulo duplicado; volumes fora de ordem ou não informados.
- A pessoa usuária escolhe agrupamento por volume, mas algum capítulo selecionado não tem volume conhecido.
- A direção muda entre exportações, existe capítulo especial, página dupla dividida ou identidade/posição de página duplicada.
- EPUB sem autor ou idioma válido, ID de publicação repetido, capa ausente, manifesto apontando para recurso inexistente ou item não listado na ordem de leitura.
- Título ou autor contém caracteres reservados de caminho, nome muito longo, acento, Unicode combinado ou tentativa de traversal.
- Pasta de saída não existe, sem permissão, sem espaço, contém arquivo de mesmo nome ou fica indisponível durante a gravação.
- Limite de tamanho é zero, inválido, menor que um pacote mínimo ou exatamente igual ao tamanho final após empacotamento.
- Parte de volume teria que cortar capítulo; uma página individual excede o limite; várias partes precisam ser nomeadas sem colisões.
- KCC não é encontrado, encontrado mas não executável, versão desconhecida, ajuda não legível, argumento mudou ou opção de saída não existe.
- KCC escreve arquivos ao lado da entrada, retorna código de saída inconsistente, cria vários resultados inesperados, falha sem mensagem, trava ou ultrapassa timeout.
- KCC inicia verificação externa de versão/avisos; a pessoa usuária não autorizou conexão.
- KCC traz padrões de título/autor/arquivo que não correspondem aos metadados fornecidos.
- KCC tenta excluir entrada, diretório ou arquivo original; arquivos de estágio ficam em volume diferente do destino final.
- Arquivo KCC termina com extensão que não revela seu tipo real, inclusive artefato dual MOBI/AZW3 com extensão MOBI.
- Leitor ou Send to Kindle aceita extensão EPUB, mas não renderiza fixed layout como esperado.
- Kindle real não está disponível para a execução manual; o resultado não pode ser anunciado como compatibilidade validada.
- O processo nativo ou externo é cancelado durante geração, validação ou gravação final.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A área Conversão deve permitir selecionar um mangá, capítulos, perfil, formatos, direção de leitura, agrupamento, divisão por tamanho e pasta local de destino. EPUB nativo é o caminho padrão; KCC é sempre opcional e deve ser escolhido explicitamente.
- **RF-002**: A exportação deve usar somente Pages e ProcessedPages locais e validados de F006. Se alguma página estiver ausente ou não processada no perfil selecionado, a aplicação deve identificar o item e não iniciar pacote incompleto.
- **RF-003**: A pessoa usuária deve escolher entre um EPUB por capítulo e EPUBs agrupados por volume. O agrupamento só pode usar volumes explicitamente conhecidos; ausência de volume deve bloquear essa opção com lista de capítulos afetados e alternativa por capítulo.
- **RF-004**: A sequência de capítulos deve seguir a ordem canônica de F004 e a ordem de página deve seguir as posições confirmadas em F006, independentemente da ordem de término de trabalhos anteriores.
- **RF-005**: A direção deve ser configurável entre direita-para-esquerda (RTL) e esquerda-para-direita (LTR). A direção inicial é RTL para um novo mangá, pode ser alterada por exportação e deve ser registrada no resultado.
- **RF-006**: EPUB deve incluir capa, título, idioma, sumário navegável com entrada por capítulo, conteúdo ilustrado, manifesto e ordem de leitura. Para exportação por capítulo, o título combina o título conhecido do mangá com o título/número fornecido para o capítulo; para volume, combina o título do mangá com o volume explicitamente conhecido. Autor só é incluído quando efetivamente informado.
- **RF-007**: Se não houver capa local fornecida, o aplicativo deve criar uma capa tipográfica neutra com o título e, se conhecido, autor, sem arte ou metadados bibliográficos inventados; a interface deve identificá-la como gerada.
- **RF-008**: Como EPUB 3 exige idioma e identificador, se o idioma não estiver informado, a interface deve pedir uma seleção válida antes da exportação. O identificador deve ser exclusivo do pacote e não pode ser apresentado como ISBN.
- **RF-009**: O EPUB deve incluir conteúdo de página em layout fixo com dimensão coerente com o DeviceProfile selecionado, capa, direção e ordem registradas. Cada página do livro deve corresponder a uma página processada, sem anexar recursos externos.
- **RF-010**: O resultado EPUB 3 nativo deve ser gerado por writer próprio que use apenas `zipfile` e `xml.etree.ElementTree` da biblioteca padrão Python 3.12. O pacote deve seguir a estrutura normativa, inclusive layout fixo, sem dependência de biblioteca EPUB de terceiros. A implementação deve ser coberta por testes de contrato e validada com EPUBCheck antes da publicação.
- **RF-011**: A estrutura final deve ser validada antes de aparecer como concluída: contêiner EPUB íntegro, metadados obrigatórios, capa, recursos referenciados presentes, sumário navegável, spine ordenado e sem referências externas ou scripts. Títulos e autores devem ser escapados como texto, não interpretados como marcação. A suíte de aceitação deve executar EPUBCheck em versão registrada e não aceitar erros de conformidade.
- **RF-012**: O EPUB nativo é o fallback quando KCC estiver ausente, incompatível, cancelado, tiver falhado ou não possuir argumento confirmado para a opção solicitada. Nenhum resultado parcial do KCC pode substituir um EPUB nativo válido.
- **RF-013**: O CBZ é opcional e deve conter os derivados processados selecionados, em sequência estável indicada por nomes ordenáveis, sem alterar ou converter os originais. CBZ não deve ser apresentado como portador universal da direção de navegação; leitores determinam sua própria configuração, e direção KCC só pode ser aplicada quando verificada para a versão/formato.
- **RF-014**: A pessoa usuária pode informar um tamanho máximo por arquivo de saída. A divisão deve medir o tamanho final, manter páginas inteiras e criar partes numeradas em fronteiras de capítulo quando possível e de página quando necessário. Nenhuma parte deve exceder o limite; se uma página sozinha exceder, a operação deve parar sem truncamento.
- **RF-015**: A divisão por tamanho deve ser aplicada apenas aos formatos cuja implementação detectada a suporte. Se uma opção KCC necessária não existir na versão instalada, a aplicação deve oferecer a divisão nativa suportada ou informar que a combinação solicitada não é compatível.
- **RF-016**: O adaptador KCC deve ser opcional, detectável por caminho configurado ou instalação disponível, sem baixar ou instalar KCC automaticamente. A detecção não deve iniciar conversão nem gerar tráfego externo.
- **RF-017**: Antes de usar KCC, o adaptador deve identificar a instalação e as capacidades da versão concreta por evidência local verificável, como versão e ajuda dessa instalação, e validar cada argumento requerido. Opções presentes somente em outra versão, no código da aplicação ou em tutoriais antigos não são suficientes.
- **RF-018**: Se as capacidades necessárias não puderem ser verificadas com segurança, o KCC deve ser marcado como incompatível para aquela solicitação; o aplicativo não pode construir argumentos CLI por suposição. Padrões do conversor que inventem título/autor ou usem nome de arquivo como metadado não podem ser aceitos; se a versão detectada não permitir fornecer metadados conhecidos e omitir autor ausente, usar EPUB nativo.
- **RF-019**: O subprocesso deve receber argumentos separados, sem shell. Entrada, saída e temporários devem ficar em áreas locais gerenciadas pela operação; nenhuma opção que exclua ou altere arquivos de entrada pode ser usada. Opções de saída só podem ser utilizadas se comprovadas na ajuda/documentação da versão detectada.
- **RF-020**: A execução KCC deve ter timeout finito configurável, padrão de 15 minutos e faixa permitida de 1 a 60 minutos, além de cancelamento. Após cancelamento, o processo deve terminar em até 5 segundos; se não encerrar nesse prazo, deve ser forçado a terminar. Resultados temporários incompletos são descartados, e originais/resultados já existentes permanecem preservados.
- **RF-021**: Se KCC iniciar conexões externas de versão ou anúncio, nenhuma execução/probe deve ocorrer sem aviso e autorização explícita por execução; quando a conexão não puder ser evitada e não for autorizada, usar EPUB nativo ou informar bloqueio. A aplicação não deve enviar conteúdo do livro a esses serviços.
- **RF-022**: A versão detectada do KCC deve ser usada para limitar formatos oferecidos. A alternativa USB deve aparecer somente quando o conversor produzir um artefato cujo suporte/estrutura tenha sido verificado; a extensão real do conversor deve ser preservada e não alterada para sugerir outro formato.
- **RF-023**: Enquanto a versão detectada documentar saída MOBI/AZW3 dual com extensão MOBI, a interface pode identificá-la como artefato dual para uso USB, mas não deve renomeá-la para .azw3 ou afirmar que é AZW3 puro sem validação.
- **RF-024**: A aplicação não deve enviar livros a Kindle, Send to Kindle, e-mail, nuvem ou terceiros. Exportar significa gravar no destino local escolhido. Qualquer transferência futura exige autorização explícita separada.
- **RF-025**: A exportação deve gravar em temporários próprios, validar o pacote e finalizar atomicamente. Nomes gerados devem ser sanitizados e não podem conter componentes de caminho fornecidos por metadados. Nunca deve sobrescrever arquivo existente sem confirmação específica; erro ou cancelamento não pode marcar Export como concluído.
- **RF-026**: ExportJob e progresso devem ser persistidos conforme F001, com estados terminais imutáveis, cancelamento, erros tipados e recuperação de resultados temporários após encerramento inesperado.
- **RF-027**: Logs devem incluir apenas estado, versão do conversor, código de saída e categoria de erro sanitizados; não registrar páginas, corpo do EPUB, título/autor, caminho absoluto, argumentos completos ou parâmetros que identifiquem conteúdo.
- **RF-028**: Geração, validação e subprocessos devem executar fora da thread gráfica; a interface deve mostrar progresso, permitir cancelamento e continuar responsiva.
- **RF-029**: Testes automatizados devem cobrir EPUB nativo, metadados faltantes, ordem/RTL, sumário/capa, volume, divisão por tamanho, CBZ, validação estrutural, KCC ausente/compatível/incompatível, argumentos variáveis, timeout, cancelamento, arquivos temporários e ausência de transferência.
- **RF-030**: A aceitação manual deve abrir em um Kindle físico um EPUB e, quando suportado, artefato KCC para USB; a verificação de fixed layout deve ensaiar separadamente Send to Kindle. Evidência deve registrar arquivo e checksum, versão de saída, modelo/geração do dispositivo, firmware, rota de transferência e resultado de capa, sumário, RTL, páginas e navegação.
- **RF-031**: EPUB com fixed layout não pode ser anunciado como compatível com Send to Kindle até o teste manual dessa rota passar. Se falhar ou não for testado, a interface/documentação deve declarar compatibilidade não verificada e oferecer somente alternativas locais efetivamente validadas.
- **RF-032**: README e documentação devem explicar formatos, agrupamento, tamanho, RTL, KCC opcional, instalação externa, restrições de rede/licença, validação e diferença entre exportar localmente e transferir para dispositivo.

### Requisitos Não Funcionais

- **RNF-001**: Interface e documentação de usuário em português brasileiro; contratos, símbolos e identificadores do código em inglês.
- **RNF-002**: Navegação, consulta de progresso e cancelamento devem responder em até 200 ms durante geração no perfil de referência F002.
- **RNF-003**: A mesma seleção, metadados, perfil, direção e configuração devem produzir mesma sequência, nomes de partes e estrutura lógica.
- **RNF-004**: Todo conteúdo permanece local até autorização específica para transferência; não fazer upload ou conexão de rede implícita.
- **RNF-005**: Arquivos-fonte e imagens processadas não podem ser alterados pela exportação; falhas devem preservar originais e último resultado válido.
- **RNF-006**: Dependências, argumentos CLI, versões e compatibilidade devem ser verificadas em documentação oficial e ambiente uv resolvido; nenhuma opção CLI pode ser inventada.
- **RNF-007**: Warnings de compatibilidade não podem ser convertidos em promessa de suporte. Resultados de teste manual são limitados ao dispositivo, firmware, arquivo e rota registrados.

### Entidades Principais

- **Export**: Contrato de F001 ampliado com formato, mangá/capítulos/páginas estáveis, agrupamento, direção, perfil, limite de tamanho, destino local, progresso, resultado, validação e estado.
- **ExportPackage**: Um arquivo final EPUB ou CBZ, ou artefato conversor verificado, com capítulos/páginas incluídos, parte e checksum.
- **ExportProfile**: Configuração validada para o leitor, dimensão, layout, direção e formato; não representa detecção real do dispositivo.
- **KccInstallation**: Instalação detectada localmente, caminho, versão identificada, capacidades e opções confirmadas; não contém credenciais.
- **ExportValidationReport**: Resultado de integridade/conformidade, erros, avisos e ferramenta/versão de validação.
- **ManualDeviceTest**: Registro de evidência por artefato, modelo, firmware, rota e critérios de leitura visual; não é telemetria enviada.
- **ExportJob**: Operação persistida, cancelável, com arquivos em preparação, progresso e saída final atômica.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: 100% dos EPUBs gerados incluem título, idioma válido, identificador exclusivo, capa, sumário por capítulo, imagens referenciadas e ordem de leitura completa.
- **CS-002**: 100% das fixtures de ordem conservam capítulos/páginas e direção selecionadas tanto no EPUB por capítulo quanto no agrupamento por volume.
- **CS-003**: 100% dos EPUBs da suíte passam a validação EPUBCheck sem erros; avisos são registrados e avaliados sem ocultação.
- **CS-004**: Em 100% dos casos acima do tamanho configurado, as partes não excedem o limite, não fragmentam imagens e não omitem/reordenam conteúdo; página individual acima do limite resulta em falha segura.
- **CS-005**: Em todas as variações do binário KCC de teste, somente argumentos presentes e compatíveis com aquela instalação são usados; binário ausente ou incompatível aciona fallback nativo sem perda de seleção.
- **CS-006**: Testes de timeout/cancelamento deixam zero processo filho ativo após o limite de encerramento e zero arquivo parcial publicado; originais permanecem byte a byte intactos.
- **CS-007**: Nenhum teste automatizado envia dados ou arquivos à rede; nenhuma conversão KCC inicia sem resolver os gates de conexão descritos.
- **CS-008**: A revisão manual registra ao menos uma combinação real de Kindle, firmware e rota; até então, fixed layout Send to Kindle permanece “não verificado”, sem afirmação de compatibilidade.
- **CS-009**: Interface e cancelamento respondem em até 200 ms no perfil F002 durante geração e validação de um volume de referência.

## Premissas

- Título do mangá existe em F001/F004; autor pode estar ausente; idioma pode estar ausente e, neste caso, a pessoa usuária deve informar idioma válido antes do EPUB.
- Capa local fornecida deve ser usada. Sem capa disponível, a saída contém somente uma capa tipográfica neutra e explicitamente gerada, sem arte atribuída à fonte.
- Seleção e ordem vêm de F004/F006. Conteúdo das páginas vem de ProcessedPages locais do perfil escolhido; saída não transforma nem sobrescreve originais.
- RTL é configurável por mangá/exportação, começa em RTL para novo mangá e altera a direção declarada; não reverte a sequência confirmada de páginas.
- Agrupamento por volume usa somente volume explicitamente fornecido. Não inferir volume de título, número de capítulo ou nome de arquivo.
- A divisão por tamanho usa limite escolhido pela pessoa usuária, não uma limitação de Send to Kindle presumida. É aplicada após a geração para medir o artefato real.
- KCC é opcional e instalado separadamente pela pessoa usuária. A disponibilidade de arquivos, modos e nomes de opção varia por versão e pacote.
- A documentação oficial atual do KCC descreve ferramentas CLI c2e/c2p e múltiplos formatos, e apresenta .mobi como artefato dual MOBI/AZW3; isto não substitui a verificação do binário instalado nem teste no dispositivo.
- A documentação atual do KCC informa conexões de versão/anúncio durante inicialização; a execução precisa respeitar opt-in de rede da pessoa usuária.
- A documentação do repositório atual do EbookLib declara licença AGPL-3.0 e suporte a EPUB2/EPUB3; a inclusão na distribuição depende de revisão de licença e versão aprovada.
- A Amazon lista EPUB entre tipos Send to Kindle, mas isso, por si só, não comprova fidelidade de layout fixo; conclusão negativa/positiva para este app requer teste manual da rota.
- O arquivo docs/roadmap.md não foi encontrado. F007 está sequenciada após F006; nenhuma dependência F008–F012 é presumida.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em ../../.specify/memory/constitution.md: arquitetura modular, operações responsivas, arquivos locais, transferências explícitas, logs sanitizados, licenças e verificação de dependências.
- F001 — Fundação do Manga to Kindle: contrato Export, DeviceProfile, estado persistente, migrações e diretório de saída local.
- F002 — Interface desktop do Manga to Kindle: área Conversão, seleção de capítulos, pasta, formato, estados, progresso, cancelamento e teclado.
- F003 — Provedores extensíveis do Manga to Kindle: regras de acesso autorizado; F007 não depende de fonte real nem faz download.
- F004 — Catálogo e capítulos do Manga to Kindle: metadados opcionais, volume, IDs e ordem canônica.
- F005 — Downloads do Manga to Kindle: Page local, identidade e ordem de páginas, hashes e preservação dos originais.
- F006 — Importação e processamento de imagens do Manga to Kindle: ProcessedPages, dimensões do perfil e imagens prontas para empacotamento.
- Biblioteca padrão Python 3.12 (`zipfile`, `xml.etree.ElementTree`) para empacotar e serializar o EPUB; nenhum writer EPUB de terceiros é incluído.
- KCC: ferramenta externa opcional, nunca instalada ou baixada pelo app. Argumentos e formatos devem vir da instalação detectada e documentação/release correspondente.
- EPUBCheck: ferramenta de validação de desenvolvimento/aceitação a fixar em versão documentada; não é necessária no caminho de execução local da pessoa usuária.
- Não foi encontrado docs/roadmap.md; a ordem e futuras dependências devem ser reconciliadas quando o roadmap existir.

### Bloqueios e Gates

- **B007-EBOOKLIB-LICENSE**: Resolvido em 25/11/2026 por decisão explícita do usuário de alterar a arquitetura para um writer próprio com a biblioteca padrão. EbookLib não será adicionado ao lock nem à distribuição.
- **B007-EPUB-FXL**: O writer próprio deve emitir as propriedades e dimensões fixed-layout definidas no EPUB 3.3 e passar EPUBCheck 5.4.0; até essa validação, não anunciar saída conformante ou compatibilidade com Send to Kindle.
- **B007-KCC-NETWORK**: A fonte oficial atual do KCC informa conexões de rede para verificação de versão/avisos durante inicialização. Não executar KCC nem consultar sua ajuda sem aviso; usar somente se a versão instalada oferecer modo sem conexões verificável ou após autorização explícita por execução. Se não autorizado, manter o fallback local.
- **B007-KCC-CAPABILITY**: Cada formato/opção solicitado depende de compatibilidade comprovada para a versão executável detectada. Ausência de confirmação bloqueia somente esse adaptador/formato, não a geração EPUB nativa aprovada.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Arquivo válido como EPUB é tratado como compatibilidade garantida no Send to Kindle. | Validar estrutura e registrar testes físicos; anunciar somente combinação efetivamente testada. |
| Versão do KCC muda opções ou padrões e corrompe saída. | Detectar versão/capacidades, verificar ajuda/documentação da instalação, usar testes de contrato e fallback sem argumentos adivinhados. |
| KCC envia telemetria/verificação sem consentimento ou registra títulos e caminhos. | Aviso por execução, opt-in de rede, logs redigidos e fallback nativo quando a conexão for recusada. |
| KCC modifica ou apaga imagens de entrada. | Usar cópias de estágio, nunca fornecer originais como destino de saída e nunca ativar opção destrutiva. |
| Writer próprio produz estrutura EPUB inválida ou fixed layout inconsistente. | Serialização com XML seguro, validação interna de pacote e EPUBCheck 5.4.0 antes de publicar. |
| Autor, idioma, volume ou ISBN são inventados para preencher metadados obrigatórios. | Exigir idioma fornecido, omitir autor/volume ausentes e usar ID técnico que não se apresenta como ISBN. |
| Divisão gera partes incompletas ou além do limite. | Medir tamanho final, dividir em fronteiras, verificar cada artefato e falhar quando uma página não cabe. |
| EPUB fixo se comporta diferente entre leitores. | Declarar limite, validar no Kindle físico e não inferir suporte Send to Kindle da aceitação geral do EPUB. |
| Arquivo anterior é apagado em falha ou saída parcialmente publicada. | Temporários, validação antes do rename final, transações recuperáveis e confirmação explícita para sobrescrever. |

### Fora do Escopo

- Upload, envio automático, sincronização em nuvem, e-mail, conexão USB ou qualquer transferência pelo aplicativo.
- Detecção/controle de dispositivo real ou promessa universal de Kindle, firmware, Send to Kindle ou layout fixo.
- Provedor remoto, download de capítulos, scraping ou retirada de B003-REAL-SOURCE.
- Conversão de imagens fonte ou edição de originais; OCR, tradução, compressão inteligente, restauração e leitura de painéis.
- Bundling, instalação automática, atualização ou redistribuição do KCC executável.
- Inventar/assumir argumentos CLI, formatos de saída, recursos, versão ou comportamento do KCC.
- Adicionar bibliotecas de autoria EPUB de terceiros sem outra decisão explícita de arquitetura/licença.
- Exportar identificadores como ISBN, nome de autor padrão do conversor ou idioma presumido do sistema.

### Estratégia de Verificação

Usar Pytest com fixtures locais para metadados, ordem, direções, covers, volumes, limites, permissões, atomicidade e recuperação. Validar pacote EPUB internamente e com versão registrada do EPUBCheck; verificar arquivos manifestados, navegação, metadados e spine. Exercitar KCC somente com executáveis simulados em testes automatizados; casos reais devem ser verificados manualmente por versão e capacidades detectadas, sem rede silenciosa. Completar a aceitação visual em Kindle físico e registrar modelo, firmware, checksum, rota USB ou Send to Kindle, resultado e limitações. Nenhum teste automatizado envia arquivos.

### Referências Verificadas

- Repositório oficial KCC: https://github.com/ciromattia/kcc — CLI, formatos, perfis, artefato dual MOBI/AZW3, comportamento de direção em CBZ, conexões de versão/avisos e licença do projeto; conferir a versão instalada antes de usar qualquer argumento.
- A especificação EPUB 3.3 do W3C: https://www.w3.org/TR/epub-33/ — pacote, layout fixo, dimensões e direção de progressão.
- O repositório oficial do EbookLib foi consultado durante a decisão, mas não é dependência da implementação: https://github.com/aerkalov/ebooklib.
- EPUB 3.3 W3C: https://www.w3.org/TR/epub-33/ — semântica da ordem do spine e direção de progressão RTL/LTR.
- EPUBCheck oficial W3C/DAISY: https://github.com/w3c/epubcheck — validador de conformidade EPUB 2/3.
- Tipos de arquivos Kindle/Send to Kindle da Amazon: https://digprjsurvey.amazon.com/csad/help/node/TNtSm13k3txFI4EvDV — lista EPUB como tipo aceito; não estabelece nesta página compatibilidade de layout fixo do artefato produzido por esta feature.
