# Especificação de Funcionalidade: F006 — Importação e Processamento de Imagens do Manga to Kindle

**Feature Branch**: 006-image-import-processing

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Importar imagens WEBP, PNG e JPEG de pastas ou CBZ autorizados, proteger leitura/extração contra traversal e excesso de recursos, apresentar prévia em ordem natural e gerar derivados para o perfil Kindle Básico 10ª geração, 600×800, sem distorção e sem alterar originais. Usar Pillow para operações de imagem; deixar recorte opcional.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Importar imagens locais com segurança (Prioridade: P1)

Como pessoa usuária, quero importar uma pasta ou arquivo CBZ autorizado para um mangá e capítulo, para manter minhas páginas organizadas localmente.

**Por que esta prioridade**: A importação local permite usar conteúdo que a pessoa já possui mesmo enquanto fontes remotas não estão autorizadas.

**Teste independente**: Selecionar uma pasta e um CBZ de fixture com imagens WEBP, PNG e JPEG, revisar a prévia ordenada e importar. Comparar hashes dos originais e testar um arquivo malicioso ou acima dos limites sem criar dados parciais.

**Cenários de aceitação**:

1. **Dado** um diretório autorizado com imagens válidas e ordenáveis, **quando** a pessoa usuária o seleciona, **então** o aplicativo apresenta uma prévia natural e permite importar para um capítulo existente vazio ou para um novo mangá/capítulo com títulos informados pela pessoa usuária.
2. **Dado** um CBZ estruturalmente válido e autorizado, **quando** a pessoa usuária o seleciona, **então** apenas imagens suportadas são consideradas, na ordem natural de seus caminhos, sem gravar nenhum caminho fornecido pelo arquivo fora da área local da aplicação.
3. **Dado** que a pessoa usuária confirma que tem autorização para processar o conteúdo, **quando** a importação é iniciada, **então** os dados permanecem no dispositivo e os arquivos de origem não são alterados.
4. **Dado** um arquivo corrompido, CBZ malicioso ou limite excedido, **quando** a pré-validação ou importação falha, **então** o aplicativo mostra a causa e não apresenta páginas parcialmente importadas.

---

### História 2 — Preparar páginas para o perfil Kindle (Prioridade: P1)

Como pessoa usuária, quero visualizar páginas corrigidas e dimensionadas para o perfil Kindle Básico 10ª geração, para obter páginas legíveis em 600×800 sem esticar a imagem.

**Por que esta prioridade**: Orientação incorreta ou distorção compromete a leitura; um perfil definido torna o resultado previsível.

**Teste independente**: Processar fixtures com orientações EXIF diferentes, imagens coloridas, em escala de cinza e com transparência; verificar dimensões, orientação, preenchimento e proporção do derivado, e confirmar que os bytes do original não mudaram.

**Cenários de aceitação**:

1. **Dado** uma imagem cuja orientação depende de EXIF, **quando** um derivado é gerado, **então** ele é exibido na orientação visual correta e o arquivo original permanece idêntico.
2. **Dado** uma imagem com proporção diferente de 600×800, **quando** o perfil é aplicado, **então** a imagem é escalada uniformemente para caber no quadro, com margens de preenchimento, sem esticar nem cortar conteúdo.
3. **Dado** uma imagem transparente ou colorida, **quando** o perfil monocromático é aplicado, **então** transparência é composta sobre branco e o derivado é convertido para escala de cinza.
4. **Dado** o processamento de uma imagem, **quando** ele é concluído, **então** o derivado tem exatamente 600×800 pixels e não substitui o original.

---

### História 3 — Revisar recorte e páginas duplas (Prioridade: P2)

Como pessoa usuária, quero revisar páginas antes de aplicar recorte ou divisão de páginas duplas, para evitar remover conteúdo ou inverter a ordem de leitura.

**Por que esta prioridade**: Recorte e divisão podem alterar o enquadramento e a sequência. A confirmação visual evita mudanças inesperadas.

**Teste independente**: Abrir páginas com margens uniformes, sem margens, conteúdo próximo às bordas e uma imagem panorâmica; confirmar que recorte vem desativado, que sua prévia não altera o original e que uma dupla dividida respeita a direção de leitura selecionada.

**Cenários de aceitação**:

1. **Dado** o perfil inicial, **quando** uma página é processada, **então** recorte de margens fica desativado por padrão e todos os pixels de conteúdo da página são preservados.
2. **Dado** que a pessoa usuária ativa o recorte, **quando** o resultado é pré-visualizado, **então** ela pode aceitar ou desativar o recorte antes da gravação final.
3. **Dado** uma imagem marcada como página dupla, **quando** a pessoa usuária habilita a divisão e escolhe a direção, **então** a imagem original gera dois derivados em ordem correspondente; sem confirmação, a imagem permanece única.
4. **Dado** que a pessoa usuária cancela importação ou processamento, **quando** a operação termina, **então** originais e páginas já confirmadas permanecem intactos e temporários incompletos são removidos ou recuperáveis.

### Casos extremos

- A pasta não existe, está vazia, inacessível, contém somente arquivos não suportados ou tem nomes que colidem no Windows por diferença de maiúsculas/minúsculas.
- Uma pasta contém links simbólicos ou pontos de nova análise; o aplicativo não deve seguir caminhos para fora da seleção.
- A extensão anuncia JPEG/PNG/WEBP, mas a assinatura real indica outro formato; a extensão não deve ser tratada como prova de conteúdo válido.
- CBZ não é um arquivo compactado válido, está criptografado, possui entradas duplicadas, nomes absolutos, caminhos com drive, UNC, separadores mistos ou segmentos de subida.
- CBZ inclui links simbólicos, entradas especiais, muitas entradas, arquivo comprimido ou expandido acima dos limites, ou tamanho declarado que não corresponde aos bytes lidos.
- Entrada de imagem está truncada, corrompida, tem MIME/formato não permitido ou dimensões que ultrapassam o limite de pixels.
- Imagem possui orientação EXIF ausente, inválida ou não padrão, paleta indexada, transparência parcial, tons de cinza ou perfil de cor.
- Recorte automático não consegue distinguir margens claras de conteúdo claro próximo à borda.
- Página dupla tem conteúdo desigual entre lados, gutter fora do centro, orientação paisagem ou direção de leitura da obra diferente do padrão.
- Importação contém nenhum arquivo de imagem válido, um só arquivo, nomes numéricos repetidos, zeros à esquerda ou diretórios aninhados.
- A pessoa usuária cancela durante leitura, decodificação, prévia, cópia original ou gravação do derivado.
- O disco fica sem espaço, perde permissão ou falha entre cópia do original, derivado e atualização do banco.
- O mangá/capítulo de destino já possui páginas de outra origem ou recebeu uma importação diferente; nenhuma página deve ser sobrescrita ou intercalada implicitamente.
- Uma importação é repetida com os mesmos arquivos, com parte dos hashes alterados ou com nomes reorganizados.
- O perfil selecionado não é Kindle Básico 10ª geração ou as preferências de margem não cabem no quadro de saída.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A aplicação deve permitir selecionar uma pasta local ou um arquivo CBZ e pré-visualizar as imagens reconhecidas antes de confirmar a importação.
- **RF-002**: A pessoa usuária deve poder importar para um mangá/capítulo existente sem páginas ou criar um mangá e capítulo locais informando seus títulos. A aplicação não deve inferir título, número ou metadados bibliográficos a partir do nome do caminho.
- **RF-003**: Antes de importar, a pessoa usuária deve confirmar que possui autorização para manter e processar o conteúdo escolhido. O aplicativo deve explicar que a confirmação não envia conteúdo a terceiros; os dados permanecem localmente.
- **RF-004**: A seleção de pasta deve percorrer subpastas sem seguir links simbólicos nem pontos de nova análise. Apenas imagens suportadas são elegíveis; demais arquivos são ignorados e contabilizados na prévia.
- **RF-005**: Pastas e CBZ devem reconhecer JPEG, PNG e WEBP sem diferenciar maiúsculas/minúsculas da extensão, e validar o conteúdo real por leitura e decodificação. Extensão divergente, arquivo inválido ou formato diferente da lista deve ser rejeitado.
- **RF-006**: A ordem padrão deve ser natural sobre o caminho relativo completo, com comparação numérica de trechos numéricos, de modo que página 2 preceda página 10. Empates devem ser resolvidos deterministicamente por caminho normalizado, ignorando diferenças de caixa primeiro e usando a forma original como desempate final.
- **RF-007**: A pessoa usuária deve poder revisar e, antes da importação, reordenar manualmente itens da prévia. A ordem confirmada deve ser preservada como posição de leitura, sem depender da ordem interna do diretório ou do arquivo compactado.
- **RF-008**: O CBZ deve ser validado antes de qualquer gravação final. A aplicação não deve extrair entradas usando nomes/caminhos fornecidos pelo arquivo; nomes absolutos, UNC, caminhos com drive, segmentos de subida, separadores ambíguos, entradas especiais/link e colisões após normalização no Windows devem rejeitar o arquivo inteiro.
- **RF-009**: CBZ criptografado ou que exija senha deve ser recusado sem tentativa de contornar a proteção. Entradas não raster, incluindo metadados e arquivos executáveis, não devem ser interpretadas nem executadas.
- **RF-010**: Limites de segurança devem abranger tanto pasta quanto CBZ: no máximo 10.000 entradas enumeradas, 5.000 imagens, 25 MiB por imagem, 2 GiB de bytes de imagem por origem e 50 megapixels decodificados por imagem. Limites devem ser verificados durante a leitura, não apenas por valores declarados no cabeçalho.
- **RF-011**: Falha em qualquer imagem elegível deve cancelar o lote inteiro antes de torná-lo visível na biblioteca. O aplicativo deve apresentar o caminho relativo sanitizado e a causa, sem salvar um lote parcial.
- **RF-012**: A importação deve copiar os bytes originais sem alteração para a área local gerenciada. A pasta de origem e o arquivo CBZ não podem ser editados, movidos ou excluídos pelo aplicativo.
- **RF-013**: A importação e o processamento devem persistir jobs, progresso, associação com mangá/capítulo, ordem de leitura e referências de original/derivado. Dados novos devem usar migração versionada; a gravação deve ser atômica ou recuperável entre banco e sistema de arquivos.
- **RF-014**: O aplicativo deve detectar uma reimportação idêntica por origem, caminho relativo normalizado e checksum, evitando duplicar páginas. Bytes iguais em posições/identidades diferentes devem ser reportados como duplicados, mas não removidos nem fundidos automaticamente.
- **RF-015**: Não é permitido importar conteúdos diferentes para um capítulo que já contenha páginas. Uma reimportação idêntica é idempotente; conflito deve ser informado e não pode sobrescrever, apagar ou reordenar páginas existentes. Mesclar fontes ou substituir páginas requer outro fluxo.
- **RF-016**: A aplicação deve incluir o perfil Kindle Básico 10ª geração com quadro de retrato de 600×800 pixels e escala de cinza. O perfil deve caber integralmente na área útil e não pode esticar nem cortar a imagem por padrão.
- **RF-017**: Pillow deve ser usado para decodificar e processar as imagens. A versão escolhida deve ser verificada para Python suportado e recursos de JPEG, PNG, WEBP e orientação EXIF antes da inclusão e resolução em uv.lock; não assumir APIs ou comportamento sem validar a documentação da versão.
- **RF-018**: A orientação EXIF deve ser aplicada ao derivado antes de outras transformações. A imagem original, inclusive seus bytes e metadados, deve permanecer intacta; o derivado não pode depender de aplicar a mesma orientação novamente.
- **RF-019**: Para saída do perfil básico, transparência deve ser composta sobre branco e a imagem deve ser convertida para escala de cinza de 8 bits. O derivado deve ser PNG em 600×800; original WEBP/PNG/JPEG permanece em formato e bytes originais.
- **RF-020**: Redimensionamento deve manter a proporção e fazer a imagem caber no quadro de 600×800 menos as margens configuradas. O espaço restante deve ser preenchido com branco; a proporção do conteúdo não pode sofrer distorção.
- **RF-021**: Margens do perfil devem ser configuráveis de 0 a 40 pixels por lado e começar em 0. Recorte de margem deve começar desativado. Quando habilitado, a prévia deve apresentar o resultado e permitir confirmar ou desfazer o recorte antes de gravar derivados.
- **RF-022**: A divisão de páginas duplas deve começar desativada e exigir que a pessoa usuária marque/ confirme cada imagem panorâmica na prévia. Com divisão habilitada, a imagem original dá origem a dois derivados: direção direita-para-esquerda usa o painel direito primeiro; direção esquerda-para-direita usa o esquerdo primeiro.
- **RF-023**: Recorte e divisão de páginas duplas devem ser opcionais e não destrutivos. Cancelar ou desativar qualquer operação não pode alterar o original. A prévia deve corresponder ao resultado que será gravado.
- **RF-024**: O processamento deve usar tarefas canceláveis e informar progresso por imagem, derivado e capítulo. Operações de disco, CBZ e Pillow não podem bloquear a thread gráfica.
- **RF-025**: Em falha ou cancelamento, temporários incompletos devem ser removidos com segurança ou reconhecidos na inicialização. Derivados finais e registros só podem ser publicados após validação; falha não pode deixar um Chapter parcialmente importado.
- **RF-026**: Falhas de permissão, disco cheio, CBZ inválido, limite excedido, imagem não suportada e decodificação devem gerar mensagens em português brasileiro com ação possível. Logs devem omitir conteúdo de livros, dados binários e caminhos absolutos sensíveis.
- **RF-027**: Testes automatizados devem cobrir tipos e modos de imagem, ordenação natural, traversal, links, limites, cancelamento, falhas de disco, migrações, atomicidade, orientação, transparência, escala de cinza, margem, recorte desativável e divisão de dupla.
- **RF-028**: README e documentação de uso devem explicar autorização local, fontes aceitas, limites, ordem natural, perfil 600×800, prévia, recorte e divisão de dupla, além da preservação dos originais.
- **RF-029**: Nenhum conteúdo importado ou processado pode ser enviado a serviços externos, Kindle, e-mail, nuvem ou terceiros nesta feature.

### Requisitos Não Funcionais

- **RNF-001**: Compatibilidade de produto permanece Windows 10/11 e Python 3.12+ definidos na constituição; interface e documentação de usuário em português brasileiro.
- **RNF-002**: Varredura, descompactação, decodificação, prévia e processamento devem executar sem bloquear a thread gráfica, com cancelamento seguro em até 200 ms para eventos de interface.
- **RNF-003**: A aplicação deve processar imagens uma por vez ou de forma limitada, respeitando limites de bytes e pixels sem carregar o arquivo CBZ inteiro ou todas as imagens decodificadas simultaneamente.
- **RNF-004**: O resultado para as mesmas imagens, parâmetros e direção de leitura deve ser determinístico, incluindo ordem, dimensão, orientação e posição dos derivados.
- **RNF-005**: 100% dos originais devem permanecer byte a byte inalterados, medidos por hash antes e depois da importação e processamento.
- **RNF-006**: A migração/recuperação deve manter o banco consistente e não apagar arquivos fora do espaço temporário gerenciado pela operação.
- **RNF-007**: Logs não podem registrar conteúdo de livros, imagens, caminhos absolutos ou dados de arquivo que identifiquem conteúdo além do necessário ao diagnóstico.
- **RNF-008**: APIs e versões de Pillow devem ser confirmadas na documentação oficial e no ambiente uv resolvido; dependências não podem ser inventadas nem atualizadas fora do fluxo do projeto.

### Entidades Principais

- **Manga**: Entidade de F001 com título obrigatório, criada localmente quando necessário somente com informação fornecida pela pessoa usuária.
- **Chapter**: Entidade de F001 associada ao mangá; título ou número é informado pela pessoa usuária quando um capítulo local novo é criado.
- **Page**: Referência local imutável ao original importado, com identidade estável e posição na ordem confirmada.
- **ProcessedPage**: Derivado separado da Page original, com identidade, posição de saída, perfil e parâmetros utilizados. Uma página dupla pode originar dois derivados ligados à mesma origem.
- **ImageImportJob**: Operação persistida de leitura, validação, prévia e importação de uma pasta ou CBZ, com progresso, cancelamento, erro e recuperação.
- **ImageProcessingProfile**: Perfil 600×800, escala de cinza, margens, opções de recorte e divisão, direção de leitura e formato de saída.
- **ImportSourceFingerprint**: Identidade estável dos arquivos selecionados e seus hashes, usada para detectar repetição sem confiar somente no nome de arquivo.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: Fixtures de pastas e CBZ com JPEG, PNG, WEBP e subpastas produzem a mesma ordem natural; em 100% dos casos de referência, 1, 2 e 10 aparecem nessa sequência.
- **CS-002**: Casos de traversal absoluto, UNC, drive, subida, link e colisão de nome são recusados antes de qualquer saída externa ou publicação parcial no banco.
- **CS-003**: Em testes nos limites imediatamente abaixo, no limite e acima, aceitação/rejeição respeita os limites de entrada, arquivo, bytes totais e pixels definidos.
- **CS-004**: 100% dos derivados do perfil medem 600×800; proporção do conteúdo é preservada com diferença de no máximo um pixel decorrente de arredondamento.
- **CS-005**: 100% das fixtures EXIF ficam visualmente orientadas corretamente; transparência termina sobre branco e o derivado é escala de cinza de 8 bits.
- **CS-006**: Com recorte desativado, nenhum pixel de conteúdo é removido; recorte habilitado só é aplicado após prévia e confirmação.
- **CS-007**: Divisão desativada mantém uma saída por original; quando confirmada, cada página dupla gera duas saídas na direção escolhida e o original permanece intacto.
- **CS-008**: Em 100% das importações canceladas ou com arquivo corrompido, não há lote parcial visível, original alterado ou temporário órfão não recuperado.
- **CS-009**: Varredura e processamento deixam navegação e cancelamento responsivos em até 200 ms no perfil de referência definido por F002.
- **CS-010**: A importação funciona sem rede e não gera requisições nem transferências externas.

## Premissas

- A pessoa usuária escolhe arquivos locais e confirma que tem autorização para mantê-los e processá-los.
- Importar não concede licença, não remove DRM e não contorna senha, CAPTCHA, autenticação ou restrição de acesso.
- O destino é um mangá/capítulo existente vazio ou um novo mangá/capítulo local com títulos informados pela pessoa usuária; nenhuma metadata é inferida do nome de arquivo.
- Ordenação natural considera caminhos relativos completos; a ordem central do CBZ e o horário do sistema de arquivos não prevalecem.
- Se existir mais de um arquivo com o mesmo conteúdo em posições distintas, todos os lugares de leitura são preservados, com aviso de conteúdo duplicado.
- Recorte começa desligado; divisão de páginas duplas também começa desligada e exige confirmação por página.
- O perfil Kindle Básico 10ª geração usa a dimensão solicitada de 600×800 em retrato, margem inicial zero, quadro branco e saída PNG em escala de cinza.
- Os limites padrão para importação são 10.000 entradas enumeradas, 5.000 imagens, 25 MiB por imagem, 2 GiB por origem e 50 megapixels por imagem. Qualquer limite menor definido por segurança ou capacidade do sistema prevalece.
- Pillow é a dependência de imagem solicitada; a versão e suporte WEBP/EXIF devem ser verificados durante o planejamento e resolução, não presumidos nesta especificação.
- O arquivo docs/roadmap.md não foi encontrado. F006 está ordenada após F005 por sequência; nenhuma dependência de F007–F012 é presumida.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em ../../.specify/memory/constitution.md: camadas, tipagem, I/O fora da interface, cancelamento, progresso, dados locais, preservação de originais, migrações e recuperação.
- F001 — Fundação do Manga to Kindle: Manga, Chapter, Page, persistência local, diretórios gerenciados, migrações e encerramento seguro.
- F002 — Interface desktop do Manga to Kindle: biblioteca, estados de tela, seleção por teclado, acessibilidade e referência de responsividade.
- F003 — Provedores extensíveis do Manga to Kindle: regras de não contorno, privacidade e ausência de provedor real não autorizado. F006 não acessa rede.
- F004 — Catálogo e capítulos do Manga to Kindle: identidade e associação de Manga/Chapter e convenções da ordem de leitura.
- F005 — Downloads do Manga to Kindle: limites de imagem, persistência de Page, arquivos originais imutáveis, progresso e recuperação de arquivos.
- Pillow: versão compatível com Python suportado e com os formatos/recursos usados deve ser confirmada na documentação oficial antes de inclusão em uv.lock.
- Não foi encontrado docs/roadmap.md; a ordem e dependências de features posteriores precisam ser conferidas quando o roadmap estiver disponível.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Entrada CBZ grava fora da pasta escolhida por path traversal. | Validar todas as entradas antes da importação e nunca confiar em nomes do arquivo como destino local. |
| ZIP bomb ou imagem enorme esgota disco/memória. | Limitar contagens, bytes comprimidos/expandidos e pixels durante leitura e decodificação. |
| Importação interrompida deixa mangá/capítulo parcialmente visível. | Preparar o lote isoladamente, publicar somente após validação e recuperar/limpar somente arquivos temporários próprios. |
| Orientação, alpha ou perfil de cor altera a leitura. | Exibir prévia determinística e preservar bytes originais; validar fixtures variadas. |
| Recorte automático remove balões ou desenhos. | Recorte desativado por padrão, prévia e confirmação explícita; manter opção de desfazer. |
| Página dupla é dividida na direção errada. | Solicitar confirmação por imagem e manter direção configurável, com direita-para-esquerda como padrão. |
| A escala distorce ou corta uma página para caber no dispositivo. | Ajustar proporcionalmente dentro de quadro, preencher margens e testar dimensões/proporção. |
| Comportamento Pillow diverge entre versões ou suporte WEBP ausente. | Selecionar e registrar versão resolvida; verificar documentação oficial e ambiente alvo Windows. |
| Conteúdo local sem autorização é processado ou compartilhado. | Confirmação de autorização, armazenamento local e ausência de qualquer transferência externa. |

### Fora do Escopo

- Consulta de provedores, rede, download remoto ou retirada do bloqueio B003-REAL-SOURCE.
- Importar arquivos com senha, contornar criptografia, DRM, CAPTCHA, login ou qualquer restrição.
- Editar os arquivos de origem, recompactar CBZ original, recomprimir originais ou apagar conteúdo selecionado.
- Mesclar várias origens em um capítulo existente, substituir páginas anteriores ou deduplicar removendo posições de leitura.
- OCR, tradução, limpeza de arte, remoção automática de balões, upscaling por IA, colorização ou restauração.
- Exportação final para PDF/EPUB/MOBI/AZW, integração com dispositivo Kindle ou envio de arquivos.
- Opções CLI, APIs internas do Pillow, classes concretas ou detalhes não confirmados pela versão da dependência.

### Estratégia de Verificação

Adicionar testes com Pytest para domínio/ordenação, processamento de imagem e apresentação. Usar fixtures pequenas com orientação EXIF, RGB, grayscale, alpha, dimensões de limite, WEBP, PNG e JPEG; CBZ válidos, corrompidos e maliciosos; e pastas com nomes numéricos e subpastas. Validar hashes dos originais, prévia e ordem, quadro final, proporção, recorte desativável, divisão conforme direção, limites, cancelamento, falha de disco, migração e recuperação após interrupção. Nenhum teste deve acessar rede.
