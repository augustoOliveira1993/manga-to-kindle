# Especificação de Funcionalidade: F007 — Exportação EPUB e KCC do Manga to Kindle

**Feature Branch**: 007-epub-kcc-export

**Criado**: 2026-11-25

**Status**: Implementação local concluída; validação física pendente

**Entrada**: Exportar páginas ilustradas como EPUB com metadados, capa, sumário, ordem e direção configurável; permitir saída por capítulo ou volume, divisão por tamanho e CBZ opcional. Gerar EPUB 3 nativamente com serialização XML e ZIP da biblioteca padrão Python, sem biblioteca EPUB de terceiros. Oferecer saída MOBI opcional pela CLI KCC 13.0.4 somente com perfil, argumentos e arquivo de saída verificados. Validar estrutura e testar manualmente em Kindle real; não prometer compatibilidade de layout fixo com Send to Kindle sem evidência. KCC não é instalado ou empacotado pelo aplicativo.

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

### História 3 — Usar KCC para MOBI ou EPUB nativo (Prioridade: P2)

Como pessoa usuária, quero usar a CLI local KCC 13.0.4 para criar MOBI ou escolher EPUB/CBZ nativo, para obter uma cópia local sem depender de instalação automática.

**Por que esta prioridade**: A CLI KCC oferece saída MOBI opcional, mas precisa ser selecionada explicitamente, verificada e não pode tornar EPUB/CBZ dependentes dela.

**Teste independente**: Validar help real capturado, incompatibilidade, ausência, timeout/cancelamento e arquivo inválido; rodar a CLI oficial KCC 13.0.4 com imagens processadas em perfil descartável; conferir publicação e preservação dos originais. A etapa final de aceitação compara a saída em um Kindle físico e registra o modelo e a rota testados.

**Cenários de aceitação**:

1. **Dado** KCC não instalado, **quando** a pessoa usuária inicia a exportação, **então** EPUB e CBZ nativos permanecem disponíveis e nenhuma instalação é baixada automaticamente.
2. **Dado** a CLI selecionada, **quando** o aplicativo verifica capacidades, **então** só aceita KCC 13.0.4 e oferece MOBI para perfis K810 (600×800) e KPW34 (1072×1448).
3. **Dado** versão incompatível, formato/perfil sem validação, ausência de idioma, limite de tamanho aplicado a MOBI ou falha KCC, **quando** a pessoa usuária tenta conversão, **então** o adaptador não executa argumentos adivinhados, preserva arquivos e informa a incompatibilidade; EPUB nativo permanece uma opção separada.
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
- A CLI selecionada não é KCC 13.0.4, ou o help não declara todas as opções obrigatórias.
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
- **RF-012**: EPUB nativo permanece independente do KCC. Falha ao solicitar MOBI deve falhar sem publicação parcial; a pessoa pode iniciar outra exportação EPUB ou CBZ.
- **RF-013**: O CBZ é opcional e deve conter os derivados processados selecionados, em sequência estável indicada por nomes ordenáveis, sem alterar ou converter os originais. CBZ não deve ser apresentado como portador universal da direção de navegação; leitores determinam sua própria configuração, e direção KCC só pode ser aplicada quando verificada para a versão/formato.
- **RF-014**: A pessoa usuária pode informar um tamanho máximo por arquivo de saída. A divisão deve medir o tamanho final, manter páginas inteiras e criar partes numeradas em fronteiras de capítulo quando possível e de página quando necessário. Nenhuma parte deve exceder o limite; se uma página sozinha exceder, a operação deve parar sem truncamento.
- **RF-015**: A divisão por tamanho está habilitada para EPUB/CBZ nativos. Em MOBI, a UI exige que o limite esteja desativado porque o comportamento de divisão KCC não foi validado.
- **RF-016**: O adaptador KCC é opcional e exige caminho escolhido pela pessoa usuária; nunca baixa, instala ou empacota KCC. Não há detecção/executável automático.
- **RF-017**: Antes de MOBI, o adaptador executa `--help` local e exige versão 13.0.4 e todas as opções usadas, incluindo formato MOBI, perfil, direção, saída, título, nome, idioma e autor.
- **RF-018**: Se versão, help, perfil ou opção não corresponder, a conversão deve parar sem argumentos adivinhados. Idioma deve ser informado; autor ausente é passado vazio para evitar o padrão KCC.
- **RF-019**: O subprocesso recebe argumentos separados e `shell=False`. Ele lê somente cópias numeradas das páginas em staging; nunca recebe caminho de originais e nunca usa opção destrutiva. Entrada/saída ficam isoladas no staging da exportação.
- **RF-020**: A execução KCC tem timeout de 15 minutos e cancelamento. Cancelamento tenta encerrar por até 3 segundos e então força o encerramento; os temporários são descartados e originais/resultados existentes permanecem preservados.
- **RF-021**: A integração aceita somente a CLI `c2e` 13.0.4 verificada; não usa GUI KCC, verificação de versão/anúncios, instalador ou serviço externo. Qualquer versão diferente é rejeitada e precisa ser revista antes de suportar.
- **RF-022**: MOBI é o único formato KCC exposto. Arquivo preserva extensão `.mobi`; não se afirma AZW3 puro, entrega USB ou compatibilidade com Kindle até validação física.
- **RF-023**: A interface não identifica MOBI como artefato dual nem o renomeia para `.azw3` sem teste correspondente.
- **RF-024**: A aplicação não deve enviar livros a Kindle, Send to Kindle, e-mail, nuvem ou terceiros. Exportar significa gravar no destino local escolhido. Qualquer transferência futura exige autorização explícita separada.
- **RF-025**: A exportação deve gravar em temporários próprios, validar o pacote e finalizar atomicamente. Nomes gerados devem ser sanitizados e não podem conter componentes de caminho fornecidos por metadados. Nunca deve sobrescrever arquivo existente sem confirmação específica; erro ou cancelamento não pode marcar Export como concluído.
- **RF-026**: ExportJob e progresso devem ser persistidos conforme F001, com estados terminais imutáveis, cancelamento, erros tipados e recuperação de resultados temporários após encerramento inesperado.
- **RF-027**: O adaptador não registra stdout/stderr, páginas, título/autor, caminho absoluto, argumentos ou conteúdo; erros exibidos usam códigos e mensagens genéricas sanitizadas.
- **RF-028**: Geração, validação e subprocessos devem executar fora da thread gráfica; a interface deve mostrar progresso, permitir cancelamento e continuar responsiva.
- **RF-029**: Testes automatizados devem cobrir EPUB/CBZ, ordem/direção, metadados, divisão, KCC ausente/incompatível, help real capturado, argumentos sem shell, timeout/cancelamento, MOBI inválido e integração com CLI oficial real quando `M2K_KCC_EXE` for definido.
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
- **B007-KCC-NETWORK**: O app chama apenas a CLI oficial `c2e` 13.0.4 escolhida explicitamente, nunca a GUI que contém verificações de versão/avisos. O entrypoint e o caminho de conversão locais foram revisados; nenhuma instalação, download, atualização ou conteúdo é enviado pelo app. Mudança de versão não é aceita sem rever o caminho de execução e a rede.
- **B007-KCC-CAPABILITY**: Help e conversões reais confirmaram somente MOBI, perfis K810/KPW34, direção, idioma, título/autor, filename e diretório de saída. Outros formatos/perfis/opções continuam bloqueados até nova evidência.

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
