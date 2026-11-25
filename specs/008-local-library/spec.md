# Especificação de Funcionalidade: F008 — Biblioteca Local do Manga to Kindle

**Feature Branch**: 008-local-library

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Consolidar a persistência local de mangás, capítulos, arquivos, exportações e progresso de downloads com SQLite, SQLAlchemy e migrações versionadas. Oferecer busca, filtros, ordenação, favoritos, histórico e identificação de capítulos já baixados. Excluir registros e arquivos somente mediante confirmação com escopo explícito.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Encontrar conteúdo na biblioteca local (Prioridade: P1)

Como pessoa usuária, quero pesquisar, filtrar e ordenar meus mangás e capítulos, para localizar rapidamente o conteúdo disponível no dispositivo.

**Por que esta prioridade**: A biblioteca é o ponto de entrada para conteúdo importado, baixado e exportado nas features anteriores.

**Teste independente**: Cadastrar fixtures de mangás/capítulos com metadados variados, favoritos e estados de arquivo; pesquisar termos com diferenças de caixa/acentos, aplicar filtros e conferir ordenação estável.

**Cenários de aceitação**:

1. **Dado** conteúdo salvo no banco local, **quando** a pessoa usuária busca título, autor, título/número de capítulo ou volume, **então** os resultados correspondentes aparecem sem acessar a rede.
2. **Dado** favoritos, capítulos baixados, parciais, importados e com arquivos ausentes, **quando** a pessoa usuária aplica filtros, **então** a biblioteca mostra somente os itens que correspondem ao estado persistido.
3. **Dado** ordenação por título, atividade recente ou número de capítulo, **quando** valores são iguais, **então** a ordenação é determinística e a identidade estável resolve empates.
4. **Dado** que o aplicativo é encerrado e reaberto, **quando** a Biblioteca carrega, **então** registros, favoritos, filtros salvos e estados conhecidos permanecem consistentes.

---

### História 2 — Consultar disponibilidade, downloads e histórico (Prioridade: P1)

Como pessoa usuária, quero ver quais capítulos já foram baixados, quais arquivos existem e como terminaram operações recentes, para saber o que está pronto sem repetir trabalho.

**Por que esta prioridade**: A fila persistente de F005 e as Pages de F006 devem se refletir no estado real da biblioteca após interrupção ou remoção externa de arquivos.

**Teste independente**: Criar trabalhos concluídos, parciais, cancelados e interrompidos, exports e arquivos faltantes; reiniciar o aplicativo e verificar classificações, progresso e histórico.

**Cenários de aceitação**:

1. **Dado** um capítulo com todas as páginas esperadas baixadas e arquivos íntegros, **quando** a Biblioteca calcula disponibilidade, **então** o capítulo aparece como “Baixado”.
2. **Dado** que existe somente parte das páginas validadas, **quando** a Biblioteca apresenta o capítulo, **então** mostra “Parcial” com progresso consistente, sem afirmar conclusão.
3. **Dado** que uma referência persistida aponta para arquivo removido ou alterado, **quando** a Biblioteca reconcilia o acervo, **então** marca “Arquivo ausente” ou “Arquivo alterado”, mantém os metadados e não baixa conteúdo novamente automaticamente.
4. **Dado** conteúdo importado localmente por F006 sem DownloadJob, **quando** a Biblioteca mostra a disponibilidade, **então** distingue “Importado localmente” de “Baixado”.
5. **Dado** um DownloadJob, ImageImportJob ou Export concluído, falho, cancelado ou interrompido, **quando** a pessoa usuária abre o histórico, **então** vê tipo, estado, data e destino/identidade permitidos sem conteúdo de páginas.

---

### História 3 — Remover registros ou arquivos com escopo explícito (Prioridade: P2)

Como pessoa usuária, quero escolher exatamente quais registros e arquivos excluir e revisar o impacto antes de confirmar, para evitar perder conteúdo por uma ação ambígua.

**Por que esta prioridade**: A biblioteca contém originais, derivados e exports em locais diferentes. Exclusão deve ser deliberada e preservar fontes e arquivos não selecionados.

**Teste independente**: Preparar um mangá com capítulos, jobs, imagens e export; cancelar a confirmação e verificar que tudo permanece. Depois confirmar somente registros e, em outro caso, registros mais arquivos específicos; conferir escopo, hashes e recuperação de falha.

**Cenários de aceitação**:

1. **Dado** uma ação de exclusão iniciada, **quando** o resumo de impacto é exibido, **então** mostra tipos e quantidades de registros, arquivos exatos, tamanho total e destinos incluídos.
2. **Dado** que a pessoa usuária cancela a confirmação, **quando** a ação termina, **então** nenhum registro, arquivo ou associação é alterado.
3. **Dado** confirmação apenas de registros, **quando** a remoção é concluída, **então** os registros selecionados e dependentes escolhidos são removidos e arquivos não selecionados permanecem rastreados como sem vínculo.
4. **Dado** confirmação de arquivos específicos, **quando** a operação termina, **então** somente arquivos listados e confirmados são removidos; originais de origem fora da área gerenciada e arquivos não selecionados permanecem intactos.
5. **Dado** falha durante exclusão de múltiplos itens, **quando** a operação é recuperada, **então** o histórico mostra quais itens foram excluídos, preservados ou ficaram ausentes e nenhuma remoção mais ampla é inferida.

### Casos extremos

- Banco SQLite inexistente, com versão antiga, migração pendente, migração interrompida, corrupção, bloqueio ou falha de permissão.
- SQLite contém registros órfãos ou constraints não habilitadas em uma conexão; inicialização deve detectar inconsistência e não apresentar sucesso normal.
- O mesmo mangá/capítulo aparece por provedores diferentes, tem título repetido ou volume ausente; IDs estáveis devem manter identidades distintas.
- Metadados opcionais de F004 não existem; busca e filtros não inventam autor, idioma, volume ou disponibilidade.
- Um job de download está em retry, pausado, cancelado, interrompido ou concluído com total de páginas desconhecido.
- Trabalho completo existe, mas página original, derivado, CBZ ou export foi apagado, movido ou alterado fora do aplicativo.
- Uma importação local existe sem DownloadJob; um capítulo tem downloads e páginas importadas com origens diferentes.
- Histórico de vários tipos tem timestamps iguais, erros repetidos ou registros vinculados a mangá removido.
- Busca não tem resultado, tem caracteres acentuados, Unicode composto/decomposto, termos com pontuação, texto longo ou entrada vazia.
- Muitos registros ou filtros combinados; ordenação por capítulo especial/decimal deve seguir F004.
- Exclusão de mangá inclui muitos capítulos, jobs e arquivos, ou a pessoa usuária seleciona somente parte do conjunto.
- Export está em execução, arquivo externo está aberto, disco fica sem espaço ou permissão é negada durante exclusão.
- Arquivo em destino de Export foi alterado depois de registrado, caminho foi redirecionado por link, ou não pertence à área controlada pelo aplicativo.
- Aplicativo encerra depois de remover arquivo mas antes de atualizar metadados, ou depois de atualizar metadados mas antes de concluir todos os arquivos.
- Uma migration em SQLite precisa alterar tabela com dados, constraint ou índice e falha durante cópia/reconstrução.
- Caminho armazenado aponta para unidade removível ou perfil de usuário mudou; a ausência não deve disparar busca remota.
- Tentativa de acesso simultâneo de sessões SQLAlchemy ou de uso da sessão da interface dentro de worker concorrente.
- Exclusão de arquivo fonte original fora da área do aplicativo é solicitada; o aplicativo deve recusar.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A Biblioteca deve persistir localmente mangás, capítulos, páginas, ProcessedPages, registros de arquivos, DownloadJobs/progresso, ImageImportJobs e Exports/saídas usando SQLite com SQLAlchemy.
- **RF-002**: O mapeamento ORM e o acesso SQLAlchemy devem permanecer na infraestrutura. Domínio e casos de uso não devem depender de modelos ORM, objetos de sessão ou detalhes de SQLite; a apresentação deve acessar dados por operações da aplicação.
- **RF-003**: Alembic deve manter revisões de esquema versionadas, com identificador e histórico aplicados. A atualização deve partir do esquema F001 e preservar todos os registros válidos produzidos por F004–F007; inicialização no esquema atual deve ser idempotente.
- **RF-004**: Migrações devem ser executadas antes de abrir a Biblioteca. Falha de migração deve interromper a inicialização normal, preservar ou permitir restaurar o estado anterior e apresentar erro acionável sem sobrescrever o banco silenciosamente.
- **RF-005**: Migrações devem ser testadas na versão Python/SQLite suportada e considerar as limitações de DDL do SQLite. Alterações que exijam reconstrução de tabela devem usar um fluxo compatível e verificável; autogeração não deve ser aplicada sem revisão.
- **RF-006**: Restrições de chave estrangeira devem estar efetivamente habilitadas em todas as conexões SQLite antes de operações e criação/migração de esquema. Inserções órfãs devem falhar; a aplicação deve verificar integridade referencial depois de migrações e recuperação.
- **RF-007**: Mangás, capítulos e páginas devem ter identidade estável, relações explícitas e unicidade de posição de página/capítulo conforme F001/F004. Metadados opcionais ausentes devem continuar ausentes.
- **RF-008**: Arquivos devem permanecer no sistema de arquivos local, não em blobs do banco. Cada registro de arquivo deve indicar categoria, vínculo, localização controlada ou destino externo, tamanho, checksum e estado conhecido.
- **RF-009**: A inicialização/reentrada na Biblioteca deve verificar referências essenciais de arquivos em segundo plano. Arquivo ausente, ilegível ou com checksum divergente deve marcar o estado correspondente e manter registros, metadados, histórico e seleção.
- **RF-010**: Reconciliar arquivo ausente não pode iniciar download, exportação ou nova consulta de fonte automaticamente. A pessoa usuária deve escolher uma ação de reparo ou retomada.
- **RF-011**: A Biblioteca deve distinguir estado “Baixado”, “Parcial”, “Não baixado”, “Importado localmente”, “Arquivo ausente/alterado” e estados de trabalho ativo, interrompido, pausado, cancelado ou falho.
- **RF-012**: “Baixado” só pode ser atribuído quando o DownloadJob estiver concluído, o total de páginas esperado for conhecido, todas as páginas estiverem registradas e seus arquivos originais existirem com integridade confirmada. Páginas importadas localmente não contam como download.
- **RF-013**: O progresso de DownloadJob, tentativas, pausa, próximo retry, interrupção e resultado por página deve permanecer persistido conforme F005. No reinício, trabalhos incompletos continuam sem iniciar rede automaticamente e exigem retomada explícita.
- **RF-014**: A biblioteca deve permitir busca local por título de mangá, autor, capítulo, número e volume, com comparação sem distinção de caixa e acentos. Campos ausentes não produzem correspondência inventada.
- **RF-015**: Filtros devem cobrir favoritos, disponibilidade de páginas (baixado/parcial/não baixado/importado/arquivo ausente), estado de download e estado de exportação; filtros podem ser combinados sem atualizar dados de origem.
- **RF-016**: A pessoa usuária deve poder marcar/desmarcar mangás e capítulos como favoritos. O estado é persistido e aplicado pelo filtro de favoritos.
- **RF-017**: Ordenação deve incluir título, atividade recente, estado e ordem numérica de capítulo definida em F004. Empates devem terminar em ordem determinística por ID estável; ausência de metadado não deve inventar posição.
- **RF-018**: A seção Histórico deve consultar os registros persistidos de DownloadJob, ImageImportJob e Export e apresentar tipo, identidade do item, início/fim, estado final e motivo sanitizado quando houver. Esses registros devem manter timestamps suficientes para o histórico; não deve existir cópia paralela de operações nem conteúdo de páginas no histórico.
- **RF-019**: Histórico não deve ser eliminado automaticamente por idade. Sua exclusão deve ocorrer somente dentro de escopo explicitamente exibido e confirmado pela pessoa usuária.
- **RF-020**: Cada ação que remove registros deve indicar se inclui mangá, capítulos, páginas, favoritos, DownloadJobs, ImageImportJobs, Exports e histórico, com quantidade de cada tipo antes de confirmar.
- **RF-021**: A pessoa usuária deve poder remover registros sem excluir arquivos. Arquivos que perderem vínculo devem permanecer rastreados como “Sem vínculo” e disponíveis para ação posterior.
- **RF-022**: Exclusão de arquivos deve ser separada ou incluída em uma confirmação explícita que enumere os arquivos exatos, categoria, tamanho e destino. Não pode haver exclusão recursiva de diretório nem inferência de arquivos por nome semelhante.
- **RF-023**: Arquivos fonte externos selecionados na F006, incluindo pastas de origem e CBZ originais, não podem ser apagados pelo aplicativo. Exclusão de arquivo é limitada a cópias e derivados gerenciados e a outputs de export registrados individualmente.
- **RF-024**: Um output de export fora da raiz gerenciada só pode ser excluído após confirmação individual do caminho exato e se a identidade/checksum registrado ainda corresponder ao arquivo; se foi alterado, deve ser preservado e sinalizado.
- **RF-025**: Exclusões devem usar plano persistido recuperável. Falha ou encerramento entre remoção de registro e arquivo deve deixar estado detectável; retomada deve concluir somente itens confirmados, sem ampliar o escopo.
- **RF-026**: Nenhuma exclusão pode sobrescrever ou modificar imagens originais; arquivos de capítulos não selecionados, exportações não selecionadas e registros não incluídos no plano devem permanecer byte a byte intactos.
- **RF-027**: A Biblioteca deve mostrar estados vazio, carregando, resultado, sem resultados, erro de banco, migração, arquivo ausente e exclusão confirmada/cancelada em português brasileiro.
- **RF-028**: Consultas, reconciliação de arquivos, migrações e exclusão não podem bloquear a thread gráfica. Progresso e cancelamento devem ser oferecidos para operações demoradas quando for seguro interromper.
- **RF-029**: Sessões SQLAlchemy devem ter escopo por operação/tarefa e não podem ser compartilhadas entre threads ou tarefas concorrentes. Mudanças em arquivos e registros devem usar fronteiras transacionais claras.
- **RF-030**: Erros de banco/arquivo devem ser traduzidos em mensagens acionáveis; logs devem omitir títulos, conteúdo de livro, caminhos absolutos, segredos e consultas de busca.
- **RF-031**: Testes automatizados devem cobrir reinício, filtros/busca, favoritos, estados de download/export, integridade referencial, migração falha/sucesso, arquivos ausentes/alterados, exclusão cancelada/confirmada e recuperação após interrupção.
- **RF-032**: README e documentação de uso devem explicar biblioteca, busca, filtros, favoritos, histórico, estado de downloads, arquivos ausentes e os dois escopos de exclusão.
- **RF-033**: A Biblioteca não deve fazer requisições de rede, consultar provedores nem enviar arquivos; todos os dados apresentados são locais e registrados pelas features anteriores.

### Requisitos Não Funcionais

- **RNF-001**: Banco e arquivos permanecem no perfil local da pessoa usuária; acesso a conteúdo não ocorre por rede.
- **RNF-002**: Nenhuma query, varredura de arquivos, migração, checksum ou operação de exclusão potencialmente bloqueante pode executar na thread gráfica.
- **RNF-003**: Busca e filtro sobre 10.000 mangás e 100.000 capítulos devem retornar a primeira página de resultados em até 500 ms no perfil de referência F002; a interface deve permanecer responsiva em até 200 ms.
- **RNF-004**: Os mesmos registros e critérios de busca/filtro/ordenação devem produzir os mesmos resultados, exceto quando atividade ou estado persistidos mudarem.
- **RNF-005**: Arquivos externos, caminhos e metadados de livros não devem ser incluídos em logs; dados de histórico devem ficar somente no SQLite local.
- **RNF-006**: Chaves estrangeiras devem ser aplicadas em toda conexão e integridade validada após inicialização, migração, exclusão e recuperação.
- **RNF-007**: Dependências e APIs de SQLAlchemy/Alembic devem ser verificadas na documentação oficial e resolvidas por uv, sem assumir defaults ou opções CLI não documentadas.
- **RNF-008**: Arquivos apontados pela biblioteca não são considerados válidos apenas por existir uma linha no banco; estado em tela deve refletir reconciliação do sistema de arquivos.

### Entidades Principais

- **Manga**: Identidade estável, título, metadados opcionais, favoritos e coleção de capítulos.
- **Chapter**: Identidade estável, referência de mangá, título/número/volume, posição canônica, favoritos e estado agregado de conteúdo.
- **Page / ProcessedPage**: Referência à imagem original imutável e aos derivados de F006, com ordem, tamanho, checksum e estado de arquivo.
- **FileAsset**: Arquivo gerenciado ou export registrado, categoria, caminho/escopo, hash, tamanho, vínculos e estado presente/ausente/alterado/sem vínculo.
- **DownloadJob / DownloadPageResult**: Trabalho, progresso e resultados persistidos conforme F005; fonte do status “Baixado”.
- **ImageImportJob**: Resultado local de importação/processamento conforme F006.
- **Export / ExportPackage**: Resultado, formato, destino e estado de exportação conforme F007.
- **LibraryActivityView**: Visão derivada dos registros persistidos de DownloadJob, ImageImportJob e Export; não duplica operações nem replica bytes ou páginas.
- **DeletionPlan**: Lista explícita dos registros e FileAssets incluídos em uma remoção confirmada, com estado recuperável.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: Após 10 ciclos de encerramento e reinício, 100% dos mangás, capítulos, favoritos, jobs, progresso e exports persistidos permanecem com os mesmos IDs, relações e estados válidos.
- **CS-002**: Tentativas de criar relação sem pai falham em todas as conexões testadas; auditoria após migração e reinício encontra zero referências órfãs.
- **CS-003**: Em 100% dos casos com arquivos removidos ou alterados fora do aplicativo, a Biblioteca os sinaliza sem apagar metadados, sem marcar capítulo como baixado e sem iniciar rede.
- **CS-004**: 100% dos resultados de busca/filtros/ordenação correspondem à fixture esperada; empates têm ordem estável e busca ignora caixa e acentos.
- **CS-005**: Em todos os cenários, “Baixado” só aparece quando todas as páginas esperadas e arquivos íntegros estão presentes; importações locais são mostradas separadamente.
- **CS-006**: 100% dos cancelamentos na confirmação de exclusão deixam registros, arquivos, hashes e vínculos inalterados.
- **CS-007**: Em 100% dos planos de exclusão confirmados, somente os registros/arquivos enumerados são removidos; originais externos e itens não selecionados preservam hash.
- **CS-008**: Falha simulada em cada etapa de migração ou exclusão deixa banco recuperável e indica precisamente o estado pendente, sem reportar sucesso falso.
- **CS-009**: Busca sobre 10.000 mangás e 100.000 capítulos retorna primeira página em até 500 ms e a interface responde em até 200 ms no perfil F002.
- **CS-010**: Todos os fluxos da Biblioteca operam sem rede e não enviam arquivos ou metadados a terceiros.

## Premissas

- F001 fornece uma base SQLite local inicial; F008 evolui o esquema sem reiniciar a base nem substituir IDs de F004–F007.
- SQLAlchemy é a camada ORM de infraestrutura. Alembic é o mecanismo de migração selecionado para revisões do esquema, sujeito à validação de compatibilidade e resolução de versões no projeto.
- SQLite exige configuração explícita de integridade referencial para cada conexão; não assumir que declarar foreign keys basta.
- Files permanecem no sistema de arquivos e o banco registra referências, checksums e estados. Conteúdo binário não é armazenado como blob no SQLite.
- Histórico significa atividades de download, importação/processamento e exportação. Histórico de leitura não está incluído porque o aplicativo não possui leitor interno definido.
- Favoritos aplicam-se a mangás e capítulos.
- “Importado localmente” é estado distinto de “Baixado”; dados de fixtures ou referências remotas não contam como arquivo local.
- Ao remover somente registros, arquivos permanecem como FileAssets sem vínculo. A exclusão dos arquivos é uma decisão separada e explícita.
- Exports escolhidos em diretório externo podem ser rastreados e removidos individualmente, mas o aplicativo nunca apaga a pasta de destino ou a fonte de importação.
- O arquivo docs/roadmap.md não foi encontrado. F008 está sequenciada após F007 e não presume requisitos de F009–F012.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição em ../../.specify/memory/constitution.md: camadas, persistência local, migrações, atomicidade, recuperação, responsividade, testes e logs sanitizados.
- F001 — Fundação do Manga to Kindle: SQLite inicial, diretórios locais, contratos Manga/Chapter/Page/DownloadJob/DeviceProfile/Export e migrações.
- F002 — Interface desktop do Manga to Kindle: áreas Biblioteca/Downloads/Conversão, estados, navegação por teclado e limite de responsividade.
- F003 — Provedores extensíveis do Manga to Kindle: IDs e capacidades de origem; F008 não realiza consultas remotas.
- F004 — Catálogo e capítulos do Manga to Kindle: metadados opcionais, identidades, volumes e ordenação canônica.
- F005 — Downloads do Manga to Kindle: DownloadJob, progresso por página, tentativas, estado retomável e arquivos validados.
- F006 — Importação e processamento de imagens do Manga to Kindle: Pages, ProcessedPages, arquivos originais/derivados e ImageImportJob.
- F007 — Exportação EPUB e KCC do Manga to Kindle: Exports, pacotes, caminhos de saída, estados e artefatos.
- SQLAlchemy ORM e Alembic: versões compatíveis com Python suportado e entre si devem ser comprovadas na documentação oficial, resolvidas com uv e registradas em uv.lock.
- Não foi encontrado docs/roadmap.md; confirmar a dependência e sequência quando o roadmap estiver disponível.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Foreign keys são declaradas mas não aplicadas pela conexão SQLite. | Habilitar a verificação em todas as conexões e testar inserção de referência órfã. |
| Migration de SQLite parece transacional mas parte do DDL é confirmada fora da transação. | Exercitar falhas na versão real de Python/SQLite, manter backup recuperável e testar restauração antes de liberar. |
| Sessão ORM compartilhada entre interface e worker causa estado concorrente. | Escopo de sessão por operação/tarefa; não compartilhar Session/AsyncSession entre tarefas. |
| Banco afirma que arquivo existe quando foi removido externamente. | Reconciliação de arquivos e estado ausente/alterado sem download automático. |
| Exclusão de mangá remove conteúdo inesperado por cascade. | Não usar cascade implícito para arquivos; criar plano de escopo e confirmação com contagens e caminhos exatos. |
| Falha entre banco e sistema de arquivos deixa referências inconsistentes. | Persistir plano de exclusão/recuperação e reconciliar cada arquivo por identidade e checksum. |
| Título ou caminho de arquivo aparece em logs. | Sanitizar logs e separar metadados de usuário de diagnóstico técnico. |
| Histórico duplicado diverge de DownloadJob/Export. | Consultar registros persistidos de operação como fonte de verdade e manter histórico sem cópia de conteúdo. |

### Fora do Escopo

- Backup em nuvem, sincronização, banco remoto ou compartilhamento multiusuário.
- Leitor integrado e histórico de leitura.
- Download automático para reparar arquivos ausentes ou nova consulta de provedores.
- Transferência para Kindle ou exclusão de arquivos fonte externos.
- Pesquisa remota, scraping, indexação do conteúdo das páginas, OCR ou busca dentro das imagens.
- Uma camada ORM no domínio ou compartilhamento de sessão SQLAlchemy entre workers.
- Opções CLI ou comportamento de SQLAlchemy/Alembic não confirmados em documentação da versão resolvida.

### Estratégia de Verificação

Usar Pytest com banco temporário local e diretórios de fixtures isolados. Cobrir migração da base F001 através das revisões F004–F008, falha e recuperação, reabertura do aplicativo, chaves estrangeiras em toda conexão, relacionamentos, estados derivados de download, busca/filtros/ordenação, favoritos, histórico e reconciliação de arquivos apagados/alterados. Para exclusões, validar plano, cancelamento, escopo de registros/arquivos, checksum, falha no meio e retomada. Medir busca em fixtures com 10.000 mangás e 100.000 capítulos. Não acessar rede.

### Referências Verificadas

- SQLAlchemy SQLite Dialect 2.0: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html — transações do sqlite3, foreign keys que exigem PRAGMA em todas as conexões e particularidades de DDL.
- SQLAlchemy ORM Session Basics: https://docs.sqlalchemy.org/en/20/orm/session_basics.html — limites de sessão, transações e rollback.
- SQLAlchemy Session API: https://docs.sqlalchemy.org/en/20/orm/session_api.html — Session não deve ser compartilhada entre threads/tarefas concorrentes.
- Alembic Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html — revisões de esquema para bancos relacionais usando SQLAlchemy.
- Alembic Batch Migrations: https://alembic.sqlalchemy.org/en/latest/batch.html — fluxo de reconstrução de tabelas para mudanças de esquema em SQLite.
