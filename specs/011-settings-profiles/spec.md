# Especificação de Funcionalidade: F011 — Configurações e Perfis do Manga to Kindle

**Feature Branch**: `011-settings-profiles`

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Gerenciar preferências locais e perfis de dispositivos: Kindle Básico 8ª e 10ª gerações como perfis padrão disponíveis, resolução retrato de 600×800, direção de leitura, escala de cinza, recorte, qualidade, concorrência, pastas, tema e política de cache. Validar valores, permitir restaurar padrões e explicar diferenças entre Kindle Básico e Paperwhite. Cobrir persistência, migração e valores inválidos.

## Histórias de Usuário e Testes

### História 1 — Escolher e manter perfis de dispositivo (Prioridade: P1)

Como pessoa usuária, quero selecionar um perfil Kindle predefinido ou criar o meu, para reutilizar parâmetros coerentes de processamento e exportação.

**Por que esta prioridade**: Um perfil validado evita configurações incompatíveis entre F006 e F007 e mantém explícito qual alvo foi usado em cada resultado.

**Teste independente**: Carregar os perfis de fábrica, selecionar Kindle Básico 8ª/10ª geração e Paperwhite 10ª geração, duplicar um perfil editável e tentar valores válidos/inválidos; conferir dimensões, direção, escala de cinza e imutabilidade dos perfis de fábrica.

**Cenários de aceitação**:

1. **Dado** uma instalação nova, **quando** a tela de configurações é aberta, **então** os perfis Kindle Básico 8ª e 10ª geração estão disponíveis em retrato 600×800, e Kindle Básico 10ª geração é o padrão ativo, em continuidade com F006.
2. **Dado** um perfil de fábrica, **quando** a pessoa usuária tenta editá-lo ou removê-lo, **então** essas ações são bloqueadas; ela pode duplicá-lo para criar um perfil personalizado.
3. **Dado** um perfil personalizado válido, **quando** é salvo e selecionado para novo processamento/exportação, **então** os novos trabalhos usam seus valores; trabalhos e resultados já registrados preservam o perfil usado originalmente.
4. **Dado** configurações inválidas ou conflitantes, **quando** a pessoa usuária tenta salvar, **então** o aplicativo explica o valor e a correção necessária e mantém o último perfil válido.

### História 2 — Ajustar preferências de leitura e processamento (Prioridade: P1)

Como pessoa usuária, quero configurar direção de leitura, escala de cinza, margens, recorte e qualidade, para preparar imagens segundo a obra e o dispositivo sem alterar originais.

**Por que esta prioridade**: Direção e processamento afetam a leitura. Defaults conservadores e prévia reduzem o risco de páginas cortadas, esticadas ou processadas de modo inesperado.

**Teste independente**: Salvar preferências válidas, reiniciar a aplicação e abrir uma prévia com recorte ligado/desligado; conferir persistência, perfil aplicado e preservação de bytes originais.

**Cenários de aceitação**:

1. **Dado** um perfil novo, **quando** suas preferências são exibidas, **então** direção inicial é RTL, escala de cinza está habilitada, margens são zero e recorte está desabilitado, de acordo com F006/F007.
2. **Dado** recorte habilitado no perfil, **quando** uma imagem é processada por F006, **então** a operação continua exigindo prévia e confirmação para cada lote e não altera a imagem original.
3. **Dado** um formato de saída sem ajuste de qualidade com perda, **quando** a pessoa usuária escolhe qualidade, **então** a interface deixa claro que esse parâmetro não se aplica e não finge alterar o resultado.

### História 3 — Configurar concorrência, pastas e cache (Prioridade: P2)

Como pessoa usuária, quero controlar o número de downloads simultâneos, os diretórios padrão e a política de cache, para adequar o uso de rede e disco ao meu computador.

**Por que esta prioridade**: Essas preferências afetam recursos e armazenamento, mas não devem ultrapassar os limites de segurança nem remover arquivos finais.

**Teste independente**: Definir concorrência e caminhos válidos, tentar limites e pastas inválidas, aplicar limpeza simulada e verificar que somente itens de cache regeneráveis podem ser removidos.

**Cenários de aceitação**:

1. **Dado** limite de concorrência configurado, **quando** F005 processa a fila, **então** usa no máximo esse número e reduz a concorrência quando a fonte exigir limite menor.
2. **Dado** uma pasta padrão de saída ou downloads alterada, **quando** o próximo trabalho é iniciado, **então** usa o novo caminho sem mover, renomear ou apagar arquivos existentes.
3. **Dado** a limpeza automática ou manual do cache, **quando** há dados expirados, **então** somente dados regeneráveis identificados como cache são removidos; originais, derivados finais, exports e arquivos de downloads permanecem intactos.

### História 4 — Restaurar padrões sem perder conteúdo (Prioridade: P2)

Como pessoa usuária, quero restaurar os valores recomendados, para corrigir uma configuração sem apagar minha biblioteca, meus perfis personalizados ou minhas credenciais.

**Por que esta prioridade**: Um retorno previsível a defaults facilita suporte e recuperação, sem transformar uma ação de configuração em operação destrutiva.

**Teste independente**: Modificar várias preferências e criar um perfil customizado; restaurar padrões, reiniciar e comparar preferências, biblioteca, exports, credenciais e perfil customizado.

**Cenários de aceitação**:

1. **Dado** preferências modificadas, **quando** a pessoa usuária escolhe “Restaurar padrões”, **então** recebe uma prévia dos valores que serão alterados e, após confirmar, os defaults são reaplicados sem excluir dados de mangás ou arquivos.
2. **Dado** um perfil personalizado ou credencial SMTP, **quando** os padrões são restaurados, **então** esses itens permanecem intactos; remoção de perfil/credencial requer ação própria e confirmação explícita.

### Casos extremos

- Perfil com nome vazio, espaços extremos, nome duplicado sem diferenciar maiúsculas/minúsculas ou nome com caracteres de caminho.
- Perfil customizado tenta dimensões ausentes, zero, negativas, fracionárias, excessivas ou área acima do limite de processamento.
- Margens somadas deixam área útil nula/negativa ou ultrapassam a resolução do perfil.
- A pessoa usuária seleciona escala colorida em perfil de dispositivo somente monocromático ou um formato que não oferece controle de qualidade.
- Direção de leitura do perfil diverge da direção do mangá ou foi sobrescrita por uma exportação F007.
- Um perfil em uso é editado, renomeado ou removido enquanto há job ativo ou histórico associado.
- Uma versão nova dos perfis internos altera resolução/capacidade enquanto a pessoa usuária tem perfis personalizados derivados dos antigos.
- A pasta foi removida, renomeada, tornou-se somente leitura, está em unidade removível ausente, tem pouco espaço, usa caminho relativo/UNC ou contém caracteres Unicode e espaços.
- Duas pastas de finalidade distinta apontam para o mesmo caminho ou uma pasta fica dentro de outra pasta gerenciada.
- Mudança do diretório padrão ocorre enquanto F005/F006/F007 tem operação ativa ou enquanto o banco ainda referencia arquivos anteriores.
- Cache contém arquivo em uso, arquivo fora do manifesto, arquivo corrompido ou conteúdo que não pode ser regenerado.
- Limpeza automática excederia o tamanho disponível ou falha por permissão/interrupção.
- Migração é interrompida entre salvar preferências, perfis, caminhos e trabalhos associados.
- Configuração antiga não tem campo novo, contém valor inválido ou versão do perfil não existe mais.
- Restaurar padrões é cancelado; nenhum valor deve mudar.
- Preferência sincronizada manualmente ou editada fora da aplicação contém valor inválido; não deve causar falha na inicialização.

## Requisitos

### Requisitos Funcionais

- **RF-001**: A área Configurações deve separar preferências gerais de perfil de dispositivo e apresentar valores atuais, defaults e validação com mensagens em português brasileiro.
- **RF-002**: A aplicação deve fornecer perfis internos e somente leitura Kindle Básico 8ª geração e Kindle Básico 10ª geração, ambos com quadro retrato 600×800, 16 níveis de cinza e densidade nominal de 167 ppi. Kindle Básico 10ª geração permanece perfil selecionado por padrão para compatibilidade com F006.
- **RF-003**: A aplicação deve fornecer um perfil interno específico Kindle Paperwhite 10ª geração com quadro retrato de 1072×1448, 16 níveis de cinza e 300 ppi, sujeito a confirmação visual/manutenção segundo referências oficiais verificadas. Gerações Paperwhite não podem ser agregadas em um perfil genérico quando diferirem em dimensões ou recursos.
- **RF-004**: A interface deve documentar diferenças entre os modelos: Kindle Básico 8ª geração tem 167 ppi e não tem luz frontal integrada; Kindle Básico 10ª geração mantém 167 ppi e adiciona luz frontal ajustável; Paperwhite 10ª geração tem 300 ppi, maior resolução, luz frontal ajustável e resistência à água IPX8. Recursos físicos informativos não devem ser tratados como opções de conversão.
- **RF-005**: Os perfis internos devem ser imutáveis e não removíveis. A pessoa usuária deve poder criar, renomear, duplicar e excluir perfis próprios; nomes devem ser únicos sem diferenciar caixa e perfis referenciados por operações em andamento não podem ser removidos até que estejam liberados.
- **RF-006**: Cada perfil deve registrar identidade/versão, nome, dispositivo/geração, largura e altura em pixels, direção padrão RTL/LTR, escala de cinza, margens, opção de recorte e preferência de qualidade aplicável.
- **RF-007**: Resolução customizada deve usar inteiros positivos, cada dimensão até 10.000 pixels e área total no máximo 50 megapixels. Valores fora da faixa devem ser recusados antes de gravar; o perfil deve preservar orientação paisagem/retrato conforme a pessoa usuária escolher.
- **RF-008**: Largura, altura e margens devem manter área útil positiva. Margens devem ficar entre 0 e 40 pixels por lado, conforme F006. A aplicação deve recusar dimensões/margens incompatíveis sem arredondar ou corrigir silenciosamente.
- **RF-009**: Direção deve aceitar somente RTL ou LTR; perfis novos devem iniciar em RTL. A preferência do perfil é padrão para novos mangás/trabalhos, mas seleção por mangá ou por exportação conforme F007 tem precedência sem reescrever resultados anteriores.
- **RF-010**: Escala de cinza deve iniciar habilitada nos perfis Kindle Básico e Paperwhite descritos nesta feature. Um perfil personalizado pode definir saída em cor apenas se o formato e o destino selecionados declararem esse suporte; a aplicação não deve anunciar compatibilidade Kindle não verificada.
- **RF-011**: Recorte deve iniciar desabilitado. Habilitá-lo no perfil não remove a exigência de prévia e confirmação definida em F006; desabilitá-lo preserva todos os pixels de conteúdo dentro das regras de dimensionamento.
- **RF-012**: Preferência de qualidade deve aceitar valores inteiros de 1 a 100, com padrão 90 para codificadores que ofereçam ajuste de qualidade com perda. Quando o formato for lossless ou não expuser essa capacidade, o controle deve ficar desabilitado ou marcado como “Não aplicável”, sem alterar conteúdo silenciosamente.
- **RF-013**: A alteração de um perfil ou preferência deve ser aplicada a novos jobs. Cada job iniciado deve guardar snapshot dos parâmetros usados; alterações posteriores não modificam uma operação em andamento, arquivo já processado ou export existente.
- **RF-014**: Concorrência global de downloads deve aceitar inteiro de 1 a 2, com padrão 2 conforme F005. O teto definido pela fonte/provedor prevalece; nenhuma configuração pode elevar o máximo da F005.
- **RF-015**: A pessoa usuária deve poder definir diretórios padrão independentes para downloads novos, exports e cache, com defaults dentro da estrutura local gerenciada definida em F001. Pastas de origem de importação continuam sendo selecionadas por operação e não são movidas pelo aplicativo.
- **RF-016**: Caminhos devem ser absolutos, normalizados, válidos no Windows e acessíveis para a finalidade. Pasta inexistente pode ser criada somente após confirmação; pasta sem permissão, dispositivo ausente, caminho inválido ou ausência de espaço deve produzir erro acionável sem mudar o valor persistido.
- **RF-017**: Alterar caminho padrão afeta somente operações novas. Não move arquivos já existentes, não troca referências no banco e não apaga diretórios antigos; movimentação da biblioteca gerenciada exige fluxo de migração separado e está fora desta feature.
- **RF-018**: Tema deve oferecer claro e escuro e iniciar em claro conforme F002. A preferência deve ser aplicada à janela e diálogos, permanecer legível/acessível e persistir após reinício.
- **RF-019**: Cache deve conter somente dados regeneráveis identificados, como prévias e miniaturas; originais importados, páginas processadas finais, downloads concluídos, exports, credenciais e logs não são cache elegível para limpeza.
- **RF-020**: Política inicial de cache deve limitar uso a 1 GiB e expirar itens sem acesso após 30 dias. A pessoa usuária pode escolher limite entre 100 MiB e 20 GiB e retenção entre 1 e 365 dias, além de limpar manualmente após conferir tamanho estimado e confirmar.
- **RF-021**: Limpeza deve remover primeiro itens de cache expirados e, se ainda exceder o teto, os menos recentemente usados. Arquivo em uso, desconhecido ou fora do manifesto de cache deve ser preservado; falhas não podem ser apresentadas como limpeza concluída.
- **RF-022**: “Restaurar padrões” deve mostrar resumo dos valores gerais que serão redefinidos e exigir confirmação. Deve restaurar perfil selecionado para Kindle Básico 10ª, RTL, escala de cinza ativa, margens zero, recorte desativado, qualidade 90, concorrência 2, tema claro, diretórios padrão e política de cache definida nesta spec.
- **RF-023**: Restaurar preferências não deve apagar biblioteca, originais, processados, downloads, exports, histórico, perfis personalizados, credenciais SMTP, notificações ou logs. Cancelar a confirmação deixa 100% dos valores inalterados.
- **RF-024**: Preferências e perfis devem ser persistidos localmente com migrações versionadas e operações atômicas ou recuperáveis. Valor inválido encontrado em configuração antiga deve ser preservado para diagnóstico local, ignorado de forma segura na ativação e apresentado com ação para corrigir/restaurar.
- **RF-025**: Migração de perfil deve preservar IDs customizados, nomes, referências de jobs e snapshots históricos. Dados anteriores sem um campo novo devem receber somente o default explicitamente definido; conteúdo ou configuração ausente não pode ser inferido.
- **RF-026**: A aplicação deve manter o valor e a unidade explícitos nos controles; mensagens devem indicar limites, conflito de pastas e capacidade não suportada antes da gravação.
- **RF-027**: Nenhum I/O de validação/criação de diretório, leitura de cache ou migração deve bloquear a thread gráfica. Operações demoradas devem exibir progresso e permitir cancelamento seguro.
- **RF-028**: Logs não devem conter credenciais, conteúdo de livros, valores de perfil sensíveis nem caminhos completos de pastas pessoais; mensagens de erro devem expor somente o necessário para corrigir a configuração.
- **RF-029**: Testes devem cobrir persistência após reinício, migração de versões anteriores, rollback/recuperação, valores válidos e inválidos, perfil padrão e customizado, recorte/cinza/direção/qualidade, concorrência, pastas, limpeza de cache, tema e restauração sem perda de dados.
- **RF-030**: README e documentação devem descrever defaults, campos, validações, alteração de pastas, efeitos em jobs novos versus existentes, limpeza de cache e diferenças de resolução/geração entre Kindle Básico e Paperwhite. As referências de hardware devem ser revalidadas antes de uma atualização de perfil.
- **RF-031**: Antes de incluir uma dependência para armazenar, validar ou manipular qualquer preferência, a equipe deve conferir documentação oficial, compatibilidade de versões e licença; não inventar APIs ou opções CLI.

### Requisitos Não Funcionais

- **RNF-001**: Compatibilidade permanece Windows 10/11, Python 3.12+ e PySide6; interface e documentação de usuário em português brasileiro, identificadores de código em inglês.
- **RNF-002**: Alterações e validações comuns de preferências devem concluir sem bloquear a janela; resposta a navegação permanece em até 200 ms conforme F002.
- **RNF-003**: Defaults, validações e resultados da mesma versão de perfil devem ser determinísticos em 100% dos testes.
- **RNF-004**: Falha ao salvar, limpar cache ou migrar deve manter a última configuração válida e deixar estado recuperável, sem apagar originais ou resultados finais.
- **RNF-005**: Preferências, perfis e paths permanecem locais; não há sincronização, telemetria ou chamadas externas iniciadas pela tela de configurações.
- **RNF-006**: O armazenamento do cache não pode exceder o teto configurado após uma limpeza concluída; em uso, o limite pode ser temporariamente ultrapassado, mas a aplicação informa a condição e agenda limpeza segura.

### Entidades Principais

- **DeviceProfile**: Perfil interno somente leitura ou perfil personalizado com identidade/versão, geração, dimensões, direção, escala de cinza, margens, recorte e qualidade aplicável.
- **ApplicationPreferences**: Perfil padrão selecionado, tema, concorrência, diretórios, retenção/teto de cache e demais valores globais.
- **ProcessingSnapshot**: Cópia imutável dos parâmetros do DeviceProfile e preferências efetivamente usados por um job/export.
- **CacheEntry**: Arquivo regenerável, finalidade, tamanho, última utilização, expiração e vínculo de segurança ao manifesto de cache.

## Critérios de Sucesso Mensuráveis

- **CS-001**: Em 100% das instalações limpas, aparecem perfis Básico 8ª e 10ª geração em 600×800 retrato e Básico 10ª é o padrão ativo.
- **CS-002**: Em 100% dos valores testados abaixo, dentro e acima dos limites, o sistema aceita somente combinações válidas e apresenta unidade/limite nos valores rejeitados.
- **CS-003**: Após 10 ciclos de reinício, 100% das preferências e perfis personalizados válidos mantêm IDs e valores; perfis de fábrica permanecem intactos.
- **CS-004**: Em 100% das migrações de fixture suportadas, os defaults novos são aplicados somente a campos ausentes, sem perder configurações, relacionamentos ou snapshots prévios.
- **CS-005**: Em 100% dos testes de processamento, o perfil usado é o snapshot escolhido no início, e modificar perfil não altera originais, derivados anteriores ou exports concluídos.
- **CS-006**: 100% dos testes de limpeza removem somente cache elegível; zero imagens originais, páginas finais, downloads, exports, credenciais e logs são removidos.
- **CS-007**: Em 100% das restaurações confirmadas, somente preferências selecionadas retornam aos defaults; biblioteca, arquivos, perfis customizados e credenciais preservam identidade e checksum.
- **CS-008**: 100% dos fluxos de tema e configurações permanecem navegáveis por teclado e legíveis em tema claro e escuro.
- **CS-009**: Validações e navegação não excedem 200 ms no perfil de referência F002, e toda operação de disco/migração potencialmente demorada ocorre fora da thread gráfica.

## Premissas

- “Kindle 8/10” significa Kindle Básico 8ª e 10ª gerações; ambos são perfis predefinidos disponíveis, com Básico 10ª como seleção padrão herdada de F006.
- Perfis de dispositivo representam parâmetros de saída, não conexão, detecção ou garantia de compatibilidade com o aparelho real.
- Papelwhite é tratado por geração. A 10ª geração é o perfil Paperwhite detalhado nesta feature; outros modelos exigem perfil próprio após verificação de documentação oficial.
- As dimensões de saída são expressas em retrato: documentos Amazon descrevem o Basic como 800×600 em pixels no eixo reportado e o Paperwhite 10ª como 1448×1072; a especificação inverte a orientação para 600×800 e 1072×1448, respectivamente.
- Qualidade com perda aplica-se somente a formatos/ferramentas que ofereçam ajuste verificável; PNG da F006 é lossless e não muda com essa preferência.
- Preferências de perfil/diretório valem para operações futuras. Resultados existentes permanecem vinculados a seu snapshot/caminho.
- O valor padrão de cache de 1 GiB e 30 dias é uma política local da aplicação, independente de limites de qualquer provedor.
- `docs/roadmap.md` não existe neste checkout. F011 foi sequenciada após F010 sem inferir requisitos de roadmap ausente.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em `../../.specify/memory/constitution.md`: dados locais, camadas, testes, responsividade, migrações, recuperação, logging seguro e idioma.
- F001 — Fundação: `DeviceProfile`, `Export`, diretórios locais, configuração e migração inicial.
- F002 — Interface desktop: área Configurações, tema claro/escuro, teclado e referência de 200 ms.
- F005 — Downloads: teto global de concorrência 2, limites mais restritivos por fonte, Retry-After e recuperação.
- F006 — Importação/processamento: profile 600×800, escala de cinza, margens 0–40, recorte opt-in e preservação de originais.
- F007 — Exportação: direção RTL/LTR, snapshots de perfil, pasta de saída, formatos e distinção entre export e transferência.
- F008 — Biblioteca local: persistência local, caminhos/checksums, migração e recuperação de arquivos ausentes.
- Documentação oficial dos dispositivos: Kindle Básico 8ª/10ª e Paperwhite 10ª geração, consultada em 2026-11-25; validar novamente antes da implementação/liberação.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Alterar um perfil afeta arquivos já processados ou jobs em execução. | Guardar snapshot imutável por job/export e aplicar configurações somente a novas operações. |
| Configuração customizada excede memória ou área de imagem suportada. | Validar dimensões, área total e margens no limite e informar o valor sem correção silenciosa. |
| Concorrência definida pelo usuário viola a fonte ou o teto da F005. | Limitar UI a 1–2 e aplicar sempre o menor teto entre configuração e capacidade documentada. |
| Limpeza confunde cache com arquivos duráveis. | Permitir remoção somente dos itens em manifesto de cache regenerável e testar hashes de arquivos que devem sobreviver. |
| Pasta padrão removida ou mídia removível desconectada. | Validar antes de cada operação, preservar referências anteriores e permitir escolher outro diretório sem mover arquivos. |
| Profile Paperwhite genérico usa dimensão errada para a geração. | Registrar geração, link de referência e dimensões por perfil; não assumir equivalência entre gerações. |
| Usuário espera que “qualidade” afete PNG ou todo conversor. | Exibir quando não aplicável e habilitar apenas parâmetros suportados e documentados pela saída selecionada. |
| Restaurar padrões é interpretado como apagar biblioteca/configuração. | Pré-visualizar escopo, confirmar e preservar conteúdo, perfis customizados e credenciais. |

### Fora do Escopo

- Detecção automática do Kindle conectado, leitura de firmware, prova de compatibilidade física ou sincronização com aparelho.
- Perfis Paperwhite de todas as gerações, Kindle Colorsoft, Scribe, Fire ou dispositivos não documentados nesta feature.
- Mover/reorganizar a raiz inteira da biblioteca gerenciada ou migrar arquivos existentes quando um caminho padrão muda.
- Apagar, recalcular ou reprocessar retroativamente imagens, downloads, exports ou jobs quando uma preferência muda.
- Instalar conversores externos, escolher argumentos KCC não verificados ou prometer efeito de qualidade em opção não suportada.
- Sincronizar configurações, perfis, cache ou credenciais com serviços de nuvem.
- Alterar política de concorrência de uma fonte além do máximo declarado ou ignorar Retry-After.
- Importar/exportar perfis em arquivo, compartilhar perfis ou sincronizá-los entre computadores.

### Estratégia de Verificação

Usar Pytest com configurações e bancos temporários. Testar valores exatamente nos limites e imediatamente abaixo/acima; perfis de fábrica/customizados, unicidade, imutabilidade, snapshots, theme, paths existentes/ausentes/sem permissão, limites de concorrência, direção, grayscale, margens, crop, qualidade lossless/lossy, cache com manifesto, expiração/tamanho e restauração cancelada/confirmada. Testar migração a partir das versões F001–F010, falha em cada etapa de gravação e reinicialização. Verificar preservação byte a byte de originais, exports e credenciais simuladas. Validar manualmente no Windows 10/11 a legibilidade dos perfis e diálogos nos dois temas. Não acessar rede nem dispositivo Kindle durante testes automatizados.

### Referências Verificadas

- Amazon, [Safety and Compliance Information for Kindle (10th Generation)](https://digprjsurvey.amazon.com/csad/help/node/GMP9ALGUF96MMD8A) — display de 6", 800×600 no eixo reportado, 167 ppi e 16 níveis de cinza.
- Amazon, [Kindle User’s Guide, 2nd Edition](https://images-na.ssl-images-amazon.com/images/I/91r6awkZtRS.pdf) — especificação 6", 800×600, 167 ppi e 16 níveis de cinza; usada para o perfil Básico legado 8ª geração.
- Amazon, [Kindle Paperwhite User’s Guide](https://images-na.ssl-images-amazon.com/images/I/81-sqj3b5bS.pdf) — especificação de 6", 1448×1072, 300 dpi e 16 níveis de cinza; normalizada para 1072×1448 em retrato.
- Amazon, [All-new Kindle Paperwhite 10th Generation](https://images-na.ssl-images-amazon.com/images/I/812Wt8KavHS.pdf) — luz integrada, tela 300 ppi, 16 níveis de cinza e resistência à água IPX8.
- Amazon, [Identify Your Kindle E-Reader](https://digprjsurvey.amazon.com/csad/help/node/GK33S847NN4V6Y83) — identifica gerações e diferenças de recursos; consultar novamente para perfis de modelos futuros.
