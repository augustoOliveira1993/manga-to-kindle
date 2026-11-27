# Especificação de Funcionalidade: F012 — Distribuição Windows do Manga to Kindle

**Feature Branch**: `012-windows-distribution`

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Preparar distribuição Windows reproduzível com PyInstaller, ícone, metadados, versão e licenças de terceiros; oferecer instalador Inno Setup opcional após revisão de licença. Não empacotar KCC ou navegadores sem verificar licença e requisitos; documentar dependências opcionais. Manter dados fora da pasta de instalação. Testar instalação, atualização e desinstalação sem apagar biblioteca sem consentimento. Criar checklist de release e validação em Windows limpo; testes ainda não executados permanecem pendentes.

## Histórias de Usuário e Testes

### História 1 — Instalar e abrir o aplicativo em Windows limpo (Prioridade: P1)

Como pessoa usuária do Windows, quero receber uma distribuição do Manga to Kindle que funcione sem instalar Python ou ferramentas de desenvolvimento, para iniciar o aplicativo com seus dados isolados da pasta dos executáveis.

**Por que esta prioridade**: A distribuição é a entrega final das features F001–F011 e deve funcionar fora do ambiente de desenvolvimento.

**Teste independente**: Em máquinas virtuais limpas de Windows 10 e 11 sem Python, `uv`, Qt ou ambiente de desenvolvimento, instalar/extrair o artefato e abrir o aplicativo; verificar versão, ícone, inicialização e criação de dados na raiz local definida por F001, fora da pasta de instalação.

**Cenários de aceitação**:

1. **Dado** um pacote de release válido e um Windows 10/11 suportado sem Python instalado, **quando** a pessoa usuária o instala ou extrai, **então** o aplicativo abre, apresenta nome/ícone/versão corretos e inicializa os dados locais sem depender do ambiente de desenvolvimento.
2. **Dado** que a instalação está em uma pasta de programas ou o pacote portátil foi extraído em outro local, **quando** o aplicativo grava configuração, banco, logs, cache, biblioteca ou preferências, **então** esses dados permanecem na raiz local de usuário estabelecida em F001 e não dentro da pasta de instalação.
3. **Dado** que uma dependência opcional externa está ausente, **quando** o aplicativo abre, **então** as funções principais continuam disponíveis e a dependência é identificada como opcional, sem download/instalação silenciosa.

### História 2 — Atualizar sem perder biblioteca e preferências (Prioridade: P1)

Como pessoa usuária, quero substituir uma versão anterior por uma nova, para receber correções sem perder mangás, capítulos, imagens, histórico, perfis ou preferências.

**Por que esta prioridade**: A biblioteca inclui registros persistentes e arquivos que ficam fora do pacote; atualizar executáveis não pode reiniciar nem mover dados de forma implícita.

**Teste independente**: Instalar uma versão anterior com banco e arquivos de fixture, fechar o aplicativo, atualizar usando o pacote novo e comparar IDs, relações, checksums, caminhos e preferências antes/depois; simular falha na migração e verificar recuperação.

**Cenários de aceitação**:

1. **Dado** uma instalação anterior válida, **quando** a pessoa usuária aplica uma atualização compatível, **então** os executáveis são atualizados e a biblioteca, os arquivos, os exports e as configurações persistem byte a byte ou mantêm os valores e checksums esperados.
2. **Dado** que a atualização requer uma migração de banco, **quando** a migração começa, **então** existe backup recuperável anterior à mudança e a aplicação só informa sucesso após confirmar que a nova versão abre os dados.
3. **Dado** migração ou instalação interrompida/falha, **quando** a recuperação ocorre, **então** os dados originais permanecem íntegros e a pessoa usuária recebe instrução acionável sem reinicialização silenciosa da biblioteca.

### História 3 — Desinstalar sem apagar dados por padrão (Prioridade: P1)

Como pessoa usuária, quero remover os executáveis sem perder minha biblioteca, para poder reinstalar, atualizar ou encerrar o uso preservando meus dados.

**Por que esta prioridade**: A desinstalação afeta um dispositivo com livros, imagens e exports locais; apagar esses dados sem consentimento não é aceitável.

**Teste independente**: Remover o aplicativo instalado com fixtures conhecidas, confirmar que a raiz de dados permanece intacta e que uma remoção de dados opcional exige confirmação separada e lista clara do escopo.

**Cenários de aceitação**:

1. **Dado** uma desinstalação padrão, **quando** ela termina, **então** executáveis, atalhos e entradas do instalador são removidos, mas a raiz de dados, biblioteca e arquivos permanecem intactos.
2. **Dado** uma opção adicional para apagar dados do usuário, **quando** a pessoa usuária a seleciona, **então** o instalador apresenta caminho e categorias exatos, exige confirmação adicional e não inclui exports externos nem arquivos que não pertencem ao escopo selecionado.
3. **Dado** que a pessoa usuária cancela a remoção de dados, **quando** a desinstalação continua, **então** nenhum conteúdo de usuário é apagado.

### História 4 — Publicar uma release rastreável e licenciada (Prioridade: P2)

Como pessoa mantenedora, quero reconstruir e verificar o pacote, identificar suas versões e entregar avisos de licenças, para publicar uma release auditável e legalmente revisada.

**Por que esta prioridade**: A distribuição agrupa dependências e conteúdo de terceiros; rastreabilidade, licenças e checklist verificável são condições de publicação segura.

**Teste independente**: Gerar o pacote a partir de checkout limpo, versão e dependências travadas; repetir a construção, conferir manifesto de componentes/hash, metadados e arquivo de avisos; bloquear publicação se houver dependência sem decisão de licença.

**Cenários de aceitação**:

1. **Dado** mesmo commit, lock de dependências e toolchain aprovados, **quando** o build é repetido em Windows, **então** produz o mesmo conjunto e versões de componentes, entradas de manifesto e comportamento; qualquer diferença binária não determinística é identificada/documentada, sem alegar reprodução bit a bit não demonstrada.
2. **Dado** uma dependência direta/transitiva ou recurso incluído sem versão/licença/atribuição verificadas, **quando** a checklist de release é revisada, **então** o gate de publicação permanece pendente e o artefato não é publicado como aprovado.
3. **Dado** uma build final, **quando** o artefato é distribuído, **então** nome, ícone, versão, origem do commit, versões de ferramentas, checksums e avisos de terceiros estão disponíveis junto da release.

### Casos extremos

- O artefato é iniciado em Windows sem Python, bibliotecas Qt, Visual C++ Runtime esperado, permissões ou espaço suficiente.
- A versão de Windows está fora do suporte declarado ou possui arquitetura de processador diferente daquela do artefato.
- A pessoa usuária não tem permissão de administrador, escolhe pasta de instalação protegida ou muda o caminho entre versões.
- A aplicação permanece aberta durante atualização ou desinstalação, banco está em uso ou um arquivo de instalação está bloqueado.
- O instalador falha depois de substituir executáveis mas antes de concluir uma migração ou registrar atalhos.
- Banco antigo está ausente, corrompido, em versão incompatível, com migração parcial ou com arquivos referenciados em unidade removível.
- O backup pré-migração não pode ser criado, está sem espaço ou tem checksum diferente.
- Desinstalação é cancelada, repetida, iniciada após dados terem sido movidos ou recebe caminho de dados alterado fora do aplicativo.
- O nome da pasta de instalação e da raiz de dados contém espaços, acentos, Unicode, caminho longo ou permissões herdadas restritas.
- Windows Defender/SmartScreen ou outro antivírus bloqueia, coloca em quarentena ou sinaliza artefato não assinado/recém-construído.
- Ícone, metadados PE, produto, editor, versão de arquivo, versão de produto e versão do instalador divergem.
- Versão de PyInstaller ou hooks da dependência alteram os arquivos empacotados, omitem DLL/plugin Qt, locale ou runtime necessário.
- Dependência transitiva muda de licença, contém aviso de redistribuição ou licença não compatível com o produto.
- F007 usa writer EPUB próprio da biblioteca padrão; EbookLib não é dependência nem componente empacotado. KCC ou Inno Setup exigem revisão/licença específica antes de inclusão.
- Navegador padrão não existe, KCC não está instalado, versão/opções não foram verificadas ou usuário não aceita tráfego opcional do KCC.
- Instalador opcional não está disponível ou sua licença não foi revisada para o modelo de distribuição; o pacote portátil precisa continuar documentado/testável.
- Atualização é downgrade ou pula versões com migrações incompatíveis; versão nova não deve corromper uma base que exige abertura por versão mais recente.
- Processo de build roda fora do Windows ou usa dependências do ambiente local que não constam em `uv.lock`.
- Testes de instalação em Windows limpo não foram executados; checklist não pode marcar como aprovado por suposição ou por teste no computador de desenvolvimento.

## Requisitos

### Requisitos Funcionais

- **RF-001**: A aplicação deve oferecer artefato de distribuição para Windows 10/11 que inclua o runtime e as dependências necessárias à inicialização, sem exigir Python, `uv`, Qt ou ferramentas de desenvolvimento na máquina da pessoa usuária. Cada release deve declarar explicitamente os pares de versão do Windows e arquitetura do processador suportados; uma combinação não testada não pode ser anunciada como suportada.
- **RF-002**: PyInstaller deve ser a ferramenta de empacotamento do aplicativo. A build Windows deve ser executada em Windows; não se deve tratar PyInstaller como compilador cruzado.
- **RF-003**: A build deve iniciar de checkout limpo, usar versão de Python compatível com a constituição e versões resolvidas/registradas para dependências do projeto e ferramenta de empacotamento. A alteração de lock ou da toolchain deve produzir uma nova entrada de build rastreável.
- **RF-004**: Opções, hooks, caminhos de dados, recursos Qt, DLLs, runtime, arquitetura e modo de saída do PyInstaller devem ser verificados na documentação da versão escolhida e no ambiente resolvido; nenhum argumento ou comportamento CLI pode ser inventado.
- **RF-005**: O artefato deve incluir ícone Windows e metadados corretos de produto, descrição, editor quando conhecido, copyright e versão; informações não conhecidas não podem ser inventadas.
- **RF-006**: O aplicativo deve usar uma versão canônica MAJOR.MINOR.PATCH para releases estáveis. Pré-lançamentos, quando publicados, devem ser identificados explicitamente. Versão da interface, metadados PE, artefato, instalador, changelog e release devem corresponder à mesma versão ou documentar a regra de mapeamento aprovada.
- **RF-007**: Cada artefato de release deve registrar commit de origem, versão do produto, versão do Python, conteúdo de `uv.lock`, versão do PyInstaller, versão/identidade do ambiente Windows de build, componentes empacotados e SHA-256 dos arquivos de saída.
- **RF-008**: Duas builds feitas com o mesmo commit, lock e toolchain em ambiente equivalente devem produzir o mesmo manifesto, versões e conteúdo funcional do pacote. Se hashes binários diferirem por metadados/temporização, essa diferença deve ser explicada; não se pode declarar reprodução bit a bit sem comparação de hashes idênticos.
- **RF-009**: A distribuição deve incluir inventário de dependências diretas e transitivas empacotadas, versão, licença/identificador quando conhecido, URL de origem, copyright e avisos/texto integral exigidos. Componentes sem decisão de compatibilidade de licença bloqueiam release.
- **RF-010**: A licença da versão escolhida de PyInstaller e suas exceções/avisos devem ser revisadas e acompanharem a distribuição conforme aplicável. A documentação oficial consultada em 2026-11-25 lista PyInstaller 6.22.3, compatibilidade com Python 3.8+ e esquema GPL-2.0 com exceção mais Apache-2.0 para certos arquivos; a versão/licença escolhida deve ser verificada novamente antes do build.
- **RF-011**: Inno Setup deve permanecer opcional. Antes de usá-lo para gerar releases, a equipe deve revisar a licença da versão do compilador e do uso da ferramenta no pipeline para o modelo do Manga to Kindle, obter licenças comerciais se exigidas e fixar/registrar versão e origem do compilador.
- **RF-012**: A saída portátil de PyInstaller deve continuar documentada e testável se Inno Setup não for escolhido/aprovado. Se o instalador for usado, deve suportar instalação por usuário como modo padrão, atualização e desinstalação com telas em português brasileiro.
- **RF-013**: Diretório de instalação e dados devem ser raízes distintas. Banco SQLite, configurações, logs, cache, biblioteca, imagens, downloads e preferências devem permanecer nos diretórios locais de usuário estabelecidos por F001/F008 e não dentro da pasta de instalação.
- **RF-014**: Criar, atualizar ou remover o aplicativo não pode reinicializar, sobrescrever ou excluir a raiz de dados. A atualização deve preservar IDs, relações, hashes, caminhos, perfis, progresso e histórico conforme aplicável.
- **RF-015**: Antes de uma atualização que exija migração persistente, deve existir backup recuperável da base e plano de recuperação. O app só pode declarar sucesso após a nova versão abrir/reconciliar os dados; falha deve permitir retorno seguro sem apagar a base anterior.
- **RF-016**: Durante atualização/desinstalação, se o aplicativo estiver aberto, o instalador deve solicitar encerramento controlado e explicar bloqueios; não deve encerrar à força ou modificar banco em uso sem confirmação e segurança.
- **RF-017**: A desinstalação padrão deve remover apenas binários/atalhos/entradas do instalador e preservar todos os dados do usuário. Remoção de dados deve ser opção separada, desmarcada por padrão, com caminho/categorias exatos e confirmação explícita.
- **RF-018**: Mesmo após confirmação de remoção de dados, exports fora da raiz gerenciada, fontes de importação, originais externos e pastas selecionadas fora do escopo devem ser preservados conforme F008. O instalador não pode apagar uma pasta externa inteira por conveniência.
- **RF-019**: Se a pessoa usuária cancelar atualização, desinstalação ou remoção de dados, a operação deve manter os dados e informar quais partes do aplicativo foram ou não removidas.
- **RF-020**: KCC não pode ser empacotado, instalado, atualizado ou redistribuído automaticamente. Sua distribuição exige revisão específica da licença, do modelo de redistribuição, dos requisitos, da versão, dos argumentos reais e do comportamento de rede definido em F007.
- **RF-021**: A distribuição padrão deve usar o navegador padrão do sistema e não empacotar navegador. Qualquer inclusão futura exige revisão/aprovação de licença, requisitos, segurança, atualização e evidência de teste; navegador ausente deve produzir alternativa manual, sem download automático.
- **RF-022**: README, `AGENTS.md` e documentação de release devem descrever formatos de distribuição, instalação/extração, requisitos de sistema validados, diretórios de dados, upgrade, backup/migração, desinstalação, dependências opcionais, comandos de build e recuperação.
- **RF-023**: Licenças e dependências opcionais devem ter seção própria na documentação. Uma dependência não incluída deve ter requisitos, versão/capacidade mínima verificada, instalação manual oficial e comportamento quando ausente, sem presumir que instalar equivale a aceitar seus termos.
- **RF-024**: Release checklist deve cobrir build, versão, licença, manifesto/avisos, hash, instalação, atualização, desinstalação, preservação de dados e smoke test em Windows limpo 10 e 11. Cada item só pode ser marcado após evidência daquela release.
- **RF-025**: Testes de instalação/upgrade/desinstalação devem usar instalações e dados descartáveis em máquinas virtuais limpas de Windows 10/11 para cada arquitetura declarada como suportada, sem Python, ferramentas de desenvolvimento, KCC ou browser empacotado; nenhum dado pessoal real pode ser usado.
- **RF-026**: Testes de upgrade devem comparar antes/depois os IDs e relações da base, checksums dos arquivos locais, preferências, exports e raiz de dados. Falhas de migração, disco cheio, cancelamento e processo aberto devem ser exercitados.
- **RF-027**: Testes de desinstalação devem provar que o modo padrão preserva biblioteca e arquivos em 100% dos cenários e que a opção destrutiva apaga somente o escopo confirmado; cancelamento preserva todos os dados.
- **RF-028**: Testes em Windows limpo ainda não executados nesta etapa de especificação devem aparecer como “Pendente” na checklist de release; não podem ser marcados como aprovados com base apenas em uma especificação ou build local.
- **RF-029**: Antes de selecionar versão de PyInstaller, Inno Setup, runtime nativo, biblioteca ou ferramenta de análise/licença, a equipe deve validar documentação oficial, suporte a Windows/Python, licença e versões; resolver dependências Python com `uv` e não inventar opções CLI.
- **RF-030**: Distribuição não deve executar operações de rede no primeiro início, baixar dependências opcionais, enviar dados, atualizar silenciosamente ou modificar arquivos do usuário.

### Requisitos Não Funcionais

- **RNF-001**: Produto distribuído permanece desktop local Windows 10/11, com interface/documentação em português brasileiro e sem necessidade de instalação de Python pela pessoa usuária.
- **RNF-002**: Instalar/atualizar/desinstalar não deve reduzir a integridade da biblioteca ou deixar banco parcialmente migrado; as operações precisam ser atômicas ou recuperáveis.
- **RNF-003**: O pacote de release deve ser rastreável e verificável por versões de entrada, manifesto e hashes criptográficos dos artefatos.
- **RNF-004**: Instalação por usuário não deve exigir privilégios administrativos, salvo se um requisito nativo comprovado exigir e aprovado; qualquer exceção deve ser informada antes da instalação.
- **RNF-005**: A distribuição deve minimizar alertas inesperados de segurança por nome/editor/metadados incorretos; assinatura digital pode ser usada quando aprovada e disponível, e estado assinado/não assinado deve ser declarado sem simulação.
- **RNF-006**: Nenhum binário, dependência opcional, licença, dados ou recurso externo pode ser redistribuído sem direitos e obrigações verificadas.
- **RNF-007**: Instalador e desinstalador não podem guardar segredos, telemetria ou conteúdo de livros, nem incluir logs de build com caminhos pessoais/credenciais.

### Entidades Principais

- **ReleaseArtifact**: Pacote portátil/instalador com nome, versão, arquitetura, formato, origem do commit, checksums e estado de validação.
- **BuildManifest**: Registro das versões e origens do Python, dependências, PyInstaller, Inno Setup opcional, arquivos, licenças, hashes e configuração de build.
- **ThirdPartyNotice**: Dependência ou recurso distribuído com versão, licença, copyright, proveniência e obrigações atendidas.
- **UserDataRoot**: Raiz local, independente da instalação, com banco, biblioteca, configurações, logs e cache mantidos através de atualizações e desinstalações padrão.
- **UpgradeBackup**: Cópia recuperável do estado persistido anterior à migração, vinculada à versão de origem e ao resultado do upgrade.
- **ReleaseChecklist**: Itens de revisão e testes com estado pendente/aprovado/reprovado e evidência por release.

## Critérios de Sucesso Mensuráveis

- **CS-001**: 100% das builds liberadas identificam commit, versão, toolchain, versões/lock, manifesto e hashes dos artefatos.
- **CS-002**: Para cada par Windows/arquitetura declarado como suportado, 100% dos smoke tests definidos em ambiente limpo sem Python/uv/Qt concluem instalação/extração, abertura, encerramento e criação de dados fora da pasta de instalação.
- **CS-003**: Em 10 ciclos de atualização de fixture, 100% dos IDs, relações, preferências e checksums de originais/derivados/exports permanecem iguais, salvo alterações explicitamente previstas por migração e registradas.
- **CS-004**: Em 100% dos testes de desinstalação padrão, biblioteca, raiz de dados e arquivos mantêm checksum; dados só são removidos após escolha e confirmação explícitas.
- **CS-005**: 100% das dependências, runtimes e componentes empacotados têm licença/aviso/restrição registrados; zero item de licença desconhecida é liberado.
- **CS-006**: 100% das dependências opcionais KCC/browser permanecem fora do artefato padrão; suas ausências não bloqueiam o caminho principal e não provocam downloads automáticos.
- **CS-007**: Builds repetidas com mesmo commit, lock e toolchain equivalente têm manifesto e conjunto de componentes idênticos; diferenças binárias residuais são identificadas e nenhuma reprodução bit a bit é declarada sem hash igual.
- **CS-008**: Nenhuma migração/atualização que falhe pode reportar sucesso ou apagar a única cópia válida da base; 100% das falhas injetadas deixam backup/restauração ou estado recuperável demonstrável.
- **CS-009**: A checklist de release registra estado e evidência de cada instalação, atualização, desinstalação, licença e Windows limpo; itens ainda não executados permanecem “Pendente”.

## Premissas

- A raiz de dados continua a área local de usuário criada em F001, com `config`, `data`, `logs` e `cache`, independente da pasta escolhida para instalar/extrair executáveis.
- Atualização significa aplicação manual de uma nova release pelo instalador/pacote, não serviço de auto-update nem download silencioso.
- A saída portátil de PyInstaller é o modo de contingência se Inno Setup não for aprovado; o instalador Inno é opcional e sua licença deve ser verificada para o uso concreto.
- PyInstaller 6.22.3 é a versão indicada pela documentação consultada em 2026-11-25, mas não está selecionada; a equipe deve escolher/pinar e testar a versão vigente no planejamento.
- A documentação de Inno Setup consultada em 2026-11-25 lista 7.1.1 e informa que usuários comerciais devem adquirir licença. O modelo de distribuição do projeto não foi definido; a aprovação/compra aplicável é gate antes de executar o compilador em release comercial.
- A matriz aprovada em 2026-11-27 é Windows 10/11 x64 somente. Até os testes correspondentes em VMs limpas, a release não pode anunciar compatibilidade comprovada para esses pares.
- No checkout revisado em 2026-11-25 não foram encontrados arquivos de implementação Python, `pyproject.toml`, `uv.lock`, configuração PyInstaller ou script Inno Setup; o `README.md` contém somente títulos. O conjunto de dependências, a arquitetura implementada e a build real ainda não são verificáveis.
- F007 usa writer EPUB da biblioteca padrão e não empacota EbookLib. KCC e Inno Setup continuam fora do pacote até revisão específica.
- KCC é uma instalação externa opcional conforme F007; navegador é fornecido pelo sistema. Ambos ficam fora do pacote até revisão específica e decisão explícita.
- O projeto ainda não possui `docs/roadmap.md` neste checkout. F012 encerra a sequência conhecida F001–F011 sem inferir conteúdo do roadmap ausente.
- Os testes de instalador, migração, desinstalação e Windows limpo não foram executados durante esta etapa de especificação; todos constam pendentes na checklist de release.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em `../../.specify/memory/constitution.md`: instalação reproduzível, versões verificadas, dados locais, migrações, recuperação, testes e documentação.
- F001 — Fundação: inicialização, encerramento seguro, raiz local, configuração, logs, SQLite e migrações.
- F002 — Interface desktop: janela, navegação, tema, metadados visíveis e estados de erro/sucesso no artefato distribuído.
- F003 — Provedores extensíveis: registro/capacidades e bloqueios de fonte real que não podem ser removidos pelo empacotamento.
- F004 — Catálogo: persistência e consulta da Biblioteca que devem sobreviver à atualização.
- F005 — Downloads: concorrência e progresso persistidos; arquivos permanecem na raiz de dados.
- F006 — Processamento: originais e derivados locais preservados.
- F007 — Exportação: saída local com writer da biblioteca padrão; KCC externo é opcional e não foi empacotado.
- F008 — Biblioteca local: referências/checksums, migrações, exclusão somente confirmada e arquivos externos protegidos.
- F009 — Envio: credenciais no cofre e sem segredos em logs/configuração que a distribuição não pode copiar.
- F010 — Atualização de capítulos: agenda local e avisos persistidos que devem ser preservados sem executar consultas durante instalação/update.
- F011 — Configurações e perfis: caminhos e preferências independentes da pasta do aplicativo.
- Documentação oficial das versões escolhidas de Python, uv, PyInstaller, PySide6/Qt e Inno Setup opcional; licenças de todos componentes diretos, transitivos e recursos distribuídos.

### Bloqueios de Release

- **B012-IMPLEMENTATION-BASELINE**: F001–F011, `pyproject.toml`, `uv.lock`, configuração PyInstaller e um bundle inicializado neste Windows 10 x64 já existem. Continuam pendentes o build a partir de checkout limpo e a compatibilidade em cada par Windows/arquitetura aprovado; até executar esses critérios, o artefato local é um rascunho e não uma release.
- **B012-ARCH-MATRIX**: Resolvido por decisão humana em 2026-11-27: Windows 10/11 x64 somente. Builds e VMs limpas para cada versão ainda são necessários para declarar compatibilidade e aprovar release.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Instalador sobrescreve ou desinstalador apaga a biblioteca. | Separar raízes de instalação e dados, preservar dados por padrão e testar checksums com VM descartável. |
| Migração falha no meio do upgrade. | Backup antes da mudança, migração recuperável, detecção de versão e teste de falha/retorno. |
| Dependência transitive tem licença incompatível ou sem aviso. | Inventário completo do conjunto empacotado, revisão de licença e gate que bloqueia release. |
| Inno Setup exige licença para uso comercial no pipeline. | Revisar termos atuais e adquirir licença se exigida; manter artefato portátil como alternativa. |
| PyInstaller omite DLL/plugin, recurso Qt ou arquivo de licença. | Build em Windows, manifesto de conteúdo e teste em Windows limpo sem ambiente de desenvolvimento. |
| Update ou setup sobrescreve arquivo em uso. | Solicitar encerramento controlado, preservar a base e não encerrar processo à força. |
| Metadados incorretos ou artefato não assinado dispara desconfiança. | Versão/editora corretas, origem e hashes publicados; declarar assinatura somente após verificação real. |
| KCC/browser incluído inadvertidamente amplia licença e superfície de atualização. | Excluir do pacote padrão e documentar instalação opcional, requisitos e licença verificada. |
| Build local depende de pacotes não registrados. | Build limpo com versões resolvidas, lock, toolchain/commit e inventário de inputs. |
| Teste em Windows limpo é marcado por inferência. | Checklist de release com itens pendentes e evidências obrigatórias por release. |

### Fora do Escopo

- Atualização automática em background, canal de atualização online, auto-download ou execução automática de instaladores.
- Distribuição macOS/Linux, Microsoft Store, winget/chocolatey, MSI, assinatura de driver ou atualização do Windows.
- Fornecer, empacotar, instalar ou atualizar navegadores, KCC, fontes de mangá ou conteúdo de terceiros.
- Alterar a decisão de F007 sobre writer da biblioteca padrão; EbookLib permanece fora do escopo e do artefato.
- Coletar telemetria, crash dumps com conteúdo, dados pessoais ou credenciais de release.
- Limpar ou compactar biblioteca durante update/uninstall; mover raiz de dados entre volumes ou perfis.
- Garantir que qualquer antivírus/SmartScreen aprove artefato unsigned em todos os equipamentos.
- Publicar release real, gerar instalador, assinar executável ou executar migrações de produção nesta etapa de especificação.

### Estratégia de Verificação

Usar Pytest e build tooling em ambiente Windows limpo/controlado com versões registradas. Validar instalação/extração em Windows 10 e 11 sem Python/uv/Qt de desenvolvimento; verificar inicialização, ícone, metadados e diretórios locais. Gerar duas builds do mesmo commit/lock e comparar manifestos, versões e hashes, registrando variações não determinísticas. Inspecionar inventário completo de dependências/licenças e os avisos entregues. Testar update da versão anterior com base/arquivos de fixture, migração bem-sucedida e falha em cada etapa, backup e recuperação. Testar app aberto, instalação cancelada, disco cheio, instalação por usuário, desinstalação padrão e opção confirmada de remoção de dados. Comparar checksums e garantir que exports externos não sejam apagados. Nenhum browser ou KCC deve ser empacotado nos testes padrão; não acessar rede no primeiro início. Todos esses testes estão **pendentes** até implementação e execução em VMs descartáveis de Windows 10/11.

### Referências Verificadas

- PyInstaller, [Manual 6.22.3](https://www.pyinstaller.org/en/stable/) — suporte documentado a Python 3.8 ou superior; ferramenta não é compilador cruzado e builds Windows são executadas em Windows.
- PyInstaller, [Licença](https://www.pyinstaller.org/en/latest/license.html) — documentação descreve licenciamento dual: GPL-2.0 com exceção para construir produtos comerciais e Apache-2.0 aplicada a certos arquivos.
- Inno Setup, [Downloads oficiais](https://jrsoftware.org/inno-setup/downloads) — consulta em 2026-11-25 lista Inno Setup 7.1.1 (2026-10-28) e 6.7.4; versões/licenças devem ser revalidadas antes do uso.
- Inno Setup, [Informações do projeto e licença](https://jrsoftware.org/inno-setup) e [Licenças comerciais](https://jrsoftware.org/inno-setup/purchase) — descreve restrições de distribuição e solicita licença comercial para usuários comerciais.
- F007, [Especificação EPUB/KCC](../007-epub-kcc-export/spec.md) — usa writer da biblioteca padrão e conserva os gates de KCC/dispositivo; exclui empacotamento automático de KCC.
