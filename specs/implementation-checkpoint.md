# Checkpoint de implementação — Manga to Kindle

Atualizado em 26/11/2026. Este checkpoint reúne as entregas locais, verificações executadas e critérios manuais pendentes. A ordem das features continua definida em [task-dependencies.md](task-dependencies.md).

## Estado dos marcos

| Marco | Estado |
|---|---|
| F002 — protótipo visual navegável | Atingido; navegação e telas base estão disponíveis. |
| F005 — primeiro download funcional | Pendente; a fila local está implementada, mas falta uma fonte com autorização verificável para habilitar o primeiro download real. |
| F006 — importação e processamento de imagens | Atingido para conteúdo local autorizado; processamento, persistência e recuperação estão implementados. A validação visual manual no Windows continua pendente. |
| F007 — MVP funcional com geração EPUB | Atingido: EPUB/CBZ nativos; MOBI integrado via CLI oficial KCC 13.0.4 nos perfis verificados. Compatibilidade física continua pendente. |
| F008 — Biblioteca Local | Atingido: consulta persistida, disponibilidade, histórico e remoção explícita implementados. A validação visual manual no Windows continua pendente. |
| F009 — fluxo de envio ao Kindle | Atingido no código: ação manual e SMTP opt-in com confirmação individual; histórico nunca afirma entrega. Testes automatizados locais passaram; validação visual no Windows e serviço externo permanecem pendentes. |
| F010 — atualização de capítulos | Infraestrutura local implementada e exercitada. O refresh real e o monitoramento permanecem bloqueados até existir uma fonte autorizada, com identidade e limites revisados; a fixture não os habilita. |
| F011 — configurações e perfis | Implementada e ligada a novas importações F006 e exports F007; validação visual no Windows continua pendente. |
| F012 — distribuição Windows | Marco local com instalador atingido: bundle `onedir` recompilado, instalado, aberto com migração `0011_mobi_export_artifacts`, atualizado e removido em perfil descartável neste Windows 10 x64. Release aprovada continua pendente da matriz, licenças/notices e VMs limpas. |

## F003 — Provedores extensíveis

**Estado**: contrato, segurança de URL e fixture offline implementados. A validação manual no Windows está pendente. `B003-REAL-SOURCE` continua aberto; nenhum provedor real ou download está habilitado.

### Evidências e testes

- `https://fixture.invalid/manga/demo` retorna sete capítulos fictícios determinísticos, sem DNS ou socket. A capacidade de download é falsa.
- IDs de capítulo não dependem da posição visual. A fixture cobre capítulos duplicados, decimais e especiais para exercitar a ordenação da F004.
- URLs inválidas, hosts não registrados, redes privadas, esquemas fora da capacidade, destinos de redirect, portas vazias e dados sensíveis são verificados sem request real.
- A consulta salva sob `provider_id=fixture` e `source_id=fixture:demo`. A integração confirma que outro registro local continua intacto e que uma URL sem provedor não recebe dados da fixture.
- Na conclusão inicial da F003: 25 testes focados e 91 testes na suíte completa passaram.
- Na revalidação compartilhada após a F004: 27 testes focados da F003 e 100 testes da suíte completa passaram.

### Critérios para validação manual

- No Windows 10/11, consultar a fixture e conferir título, identificação de demonstração e ordem `1, 1, 1.5, 2, 10`, seguida dos dois bônus.
- Consultar uma URL externa não registrada e um esquema FTP; confirmar mensagens adequadas e ausência de fallback para a fixture.
- Confirmar navegação por teclado e leitura dos rótulos de demonstração.
- A tela Biblioteca ainda mostra um exemplo visual fixo; ela não lista o catálogo persistido. A preservação de outro registro local foi verificada pela integração automatizada.

O roteiro está em [quickstart F003](003-extensible-providers/quickstart.md).

## F004 — Catálogo e capítulos

**Estado**: fluxo offline de consulta, ordenação, seleção e refresh recuperável implementado. Validação visual manual no Windows pendente. A F004 não habilita fontes externas, baixa capas ou capítulos nem altera imagens.

### Evidências e testes

- A consulta da fixture roda em worker e mostra metadados ausentes como “Não informado”. Capítulos são ordenados por número explícito, com decimais, desempate estável e especiais no final.
- O intervalo de capítulos é inclusivo e substitui a seleção anterior; IDs ainda presentes mantêm a seleção após refresh.
- Uma falha ou cancelamento preserva o último snapshot. A interface mantém o catálogo válido visível, indica que ele é anterior e permite tentar novamente; sair da tela cancela a consulta.
- A persistência é transacional. Um teste confirma que atualizar a fixture não altera outro registro local.
- A suíte focada da F004 passou: `32 passed`. A suíte completa passou: `100 passed`.
- Inicialização/encerramento desktop: `2 passed`. Ruff: `All checks passed`. MyPy: `Success: no issues found in 67 source files`.

### Critérios para validação manual

- No Windows 10/11, conferir layout, foco e mensagens em português nos temas claro e escuro.
- Conferir a ordem da fixture, selecionar um item e depois um intervalo com extremos invertidos que atravesse os bônus; itens de fora devem ficar desmarcados.
- Atualizar e conferir a seleção preservada. Depois informar uma URL não suportada e confirmar que o catálogo anterior permanece visível e selecionável.
- Confirmar que a consulta da fixture não abre conexão de rede. O teste automatizado também verifica resposta da interface abaixo de 200 ms enquanto uma consulta de teste aguarda no worker.
- O cancelamento com uma operação demorada é exercitado por teste; a fixture termina rápido demais para demonstrar essa janela manualmente.

O roteiro está em [quickstart F004](004-catalog-chapters/quickstart.md).

## F005 — Fila de downloads

**Estado**: engenharia da fila local concluída; o marco do primeiro download funcional permanece bloqueado por `B003-REAL-SOURCE`. Não existe provider de produção nem adaptador HTTP habilitado. O transporte injetável só é usado com respostas de teste automatizadas e não conta como funcionalidade simulada disponível no produto.

### Evidências e testes

- A tela Downloads lista trabalhos persistidos e mostra progresso por capítulo/página; pausa, retomada explícita e cancelamento são conectados ao estado local. A fixture F003 não pode criar trabalho, e a interface explica que não há fonte autorizada.
- A fila limita transferências simultâneas, aplica retry/rate limit documentados, valida destino/resposta e imagem raster, grava por staging e promoção atômica e reconcilia operações interrompidas sem iniciar rede na retomada.
- A suíte focada F005 passou: `37 passed`. A suíte completa `uv run --locked --python 3.12 pytest tests -q` passou: `129 passed`. Inicialização/encerramento desktop: `2 passed`. Ruff: `All checks passed`. MyPy: `Success: no issues found in 79 source files`.
- Não foi adicionada dependência HTTP nem Pillow; `pyproject.toml` e `uv.lock` permanecem sem mudança para F005. A aplicação só poderá habilitar uma fonte depois de revisão de autorização, hosts, limites e política.

### Critérios para validação manual

- No Windows 10/11, abrir Downloads e conferir o estado sem fonte autorizada, botão de início desativado, foco/teclado e rótulos acessíveis.
- Consultar a fixture, selecionar capítulos, voltar a Downloads e confirmar que a fila continua vazia; reiniciar a aplicação e confirmar que nenhum tráfego começa automaticamente.
- O primeiro download real, progresso/controles com conteúdo real e a verificação de origem autorizada dependem de evidência oficial compatível com download e uso local. Esse é o bloqueio do marco F005; não há tráfego real a executar até resolver o gate.

O roteiro está em [quickstart F005](005-download-queue/quickstart.md).

## F006 — Importação e processamento de imagens

**Estado**: importação local de pastas e CBZ autorizados, prévia ordenável, perfil 600×800 padrão, perfis F011 selecionáveis, recorte opcional e divisão manual de páginas duplas RTL/LTR implementados. O aplicativo permanece local: preserva originais, publica derivados separadamente e não acessa rede.

### Evidências e testes

- A origem aceita JPEG, PNG e WEBP, aplica ordem natural revisável, valida o conteúdo decodificado e impõe limites de 10.000 entradas, 5.000 imagens, 25 MiB por imagem, 2 GiB por lote e 50 megapixels por imagem. CBZ é lido em streaming, sem extração de caminhos externos; entradas inseguras rejeitam o lote.
- Originais e derivados são armazenados em diretórios separados por operação. O banco registra hash, metadados, estado/progresso e perfil; publicação usa staging e renomeação atômica, e inicialização marca jobs interrompidos para reconciliação.
- `examples/demo-import/pasta` e `demo.cbz` contêm apenas ilustrações geométricas sintéticas; não são importados automaticamente nem alteram dados reais. O roteiro manual está em [quickstart F006](006-image-import-processing/quickstart.md).
- Os testes focados da F006 passaram: `40 passed`. A primeira suíte completa revelou uma expectativa antiga de cinco telas; após ajustar navegação e teste, a suíte completa passou: `169 passed` em 31,26s.
- Pillow 13.0.0 está resolvido em `uv.lock`; runtime Python 3.12 confirmou JPEG e WEBP e a API de EXIF transpose. Pillow é dependência da F006 (a F005 não adicionou cliente HTTP).
- Inicialização real no Windows, com `uv run --locked --python 3.12 manga-to-kindle` e plataforma Qt offscreen, permaneceu ativa, registrou startup completo e aplicou a migração `0004_image_import`; banco confirmou as tabelas `image_import_job` e `processed_page`. O processo de smoke test foi encerrado após a checagem; nenhum exemplo foi importado.
- Ruff: `All checks passed`. MyPy: `Success: no issues found in 96 source files`.
- Comando exato para iniciar: `uv run --locked --python 3.12 manga-to-kindle` (após `uv sync --locked --python 3.12`).

### Critérios para validação manual

- No Windows 10/11, conferir foco, contraste, rótulos acessíveis, ordenação/reordenação e prévias para JPEG, PNG, WEBP, EXIF e transparência.
- Conferir o recorte com conteúdo claro perto das bordas e revisar que a página panorâmica se divide na ordem RTL/LTR marcada.
- Confirmar destino novo e existente, reimportação idempotente, conflito sem sobrescrita e preservação dos bytes na origem.
- Exercitar cancelamento com lote grande, disco lento/cheio e reinício durante staging; nenhum lote parcial deve aparecer.
- Confirmar ausência de rede/transferência. O roteiro está em [quickstart F006](006-image-import-processing/quickstart.md).

## F007 — Exportação EPUB/CBZ e MOBI local

**Estado**: MVP funcional com geração EPUB atingido. EPUB/CBZ nativos e o adaptador opcional MOBI KCC 13.0.4 foram integrados. Nenhum arquivo é transferido automaticamente; Kindle físico/Send to Kindle não foram validados.

### Evidências e testes

- `CreateExport` continua consumindo somente páginas processadas F006, publica com staging atômico e grava formato, caminho e hash na Biblioteca. A migração `0011_mobi_export_artifacts` permite persistir MOBI; a listagem F009 filtra exclusivamente EPUB, evitando exposição de MOBI ao envio.
- O usuário autorizou writer EPUB próprio usando biblioteca padrão; EbookLib não é dependência. A fixture passou pelo EPUBCheck 5.4.0: **0 erros fatais, 0 erros e 0 advertências**.
- CLI oficial KCC v13.0.4 Windows x64, escolhida manualmente para validação: SHA-256 `AC245FE431063875CBE5290731094356655ACCCE3217048AE3ECB7E63F210C22`, Authenticode válido, SignPath Foundation. Help capturado e proveniência estão em `tests/fixtures/kcc/`; nenhum binário foi copiado ao repositório ou bundle.
- Conversões reais de imagens sintéticas foram executadas: MOBI K810 (600×800), MOBI KPW34 (1072×1448) e EPUB K810; saída MOBI carregou assinatura `BOOKMOBI` no byte 60. A integração real F006→KCC→MOBI→SQLite foi executada com KCC 13.0.4 e confirmou originais intactos e MOBI inelegível para F009.
- Suíte focada F007 incluindo startup, migração e integração KCC real: `54 passed em 21,05s`. F012 packaging depois do rebuild: `24 passed em 23,16s`, incluindo smoke do bundle/instalador na revisão `0011_mobi_export_artifacts`.
- Regressão final: `uv run --locked --python 3.12 pytest tests -q` — **363 passed em 133,91s** com `M2K_KCC_EXE` apontando para a CLI real; o teste KCC não foi ignorado. Ruff: **All checks passed**. MyPy nos módulos do app e release: **153 arquivos sem issues**.
- Comando exato para iniciar: `uv run --locked --python 3.12 manga-to-kindle` após `uv sync --locked --python 3.12`. Dados sintéticos ficam em `examples/demo-import` e são importados somente quando a pessoa usuária os seleciona.

### Critérios de aceitação para validação manual

- No Windows 10/11, conferir foco/teclado/leitor de tela, tema, rolagem, seleção do KCC, estado de progresso/cancelamento e confirmação de caminho.
- Importar os exemplos sintéticos em perfil temporário e testar EPUB, CBZ e MOBI; confirmar que EPUB/CBZ continuam disponíveis sem KCC, idioma explícito no MOBI, perfis K810/KPW34, colisão sem sobrescrita e cancelamento sem arquivos parciais.
- Abrir EPUB/MOBI em leitores locais e registrar observações. Para aceitação em dispositivo Kindle, registrar checksum, modelo/geração, firmware, rota USB ou Send to Kindle e resultado de capa, páginas, sumário e direção; permanece pendente.
- Não afirmar suporte físico, MOBI via Send to Kindle, AZW3 puro nem entrega antes da validação correspondente.

### Disponível e ainda pendente

- Disponível: EPUB 3 nativo fixo e CBZ; MOBI via CLI oficial KCC 13.0.4 explicitamente escolhida, apenas 600×800/K810 ou 1072×1448/KPW34; histórico SQLite/Biblioteca, preservação de originais e exclusão do MOBI do fluxo de envio.
- Limites: divisão por tamanho só para EPUB/CBZ; MOBI requer idioma, usa autor vazio se ausente, e não é enviado pelo F009. KCC não é baixado/instalado ou empacotado.
- Ainda pendente: compatibilidade física Kindle e aceitação EPUB fixed-layout via Send to Kindle. Downloads F005 e atualização remota F010 continuam bloqueados por falta de fonte autorizada.

O roteiro e os passos de teste estão em [quickstart F007](007-epub-kcc-export/quickstart.md).

## F008 — Biblioteca Local

**Estado**: concluída e conectada ao SQLite local. A tela consulta catálogos, importações, downloads registrados e exports; não popula demonstrações automaticamente e não acessa rede. Exclusões exigem prévia e confirmação; pastas de origem, arquivos compartilhados e conteúdo alterado ficam protegidos.

### Funcionalidades e evidências

- Busca local por título, autor, capítulo, número e volume, sem distinção de caixa/acentos; filtros de favorito, disponibilidade, download e exportação; ordenação estável; preferências persistidas.
- Disponibilidade reconcilia existência e checksum das páginas originais/derivadas e exports. Download só aparece como concluído quando o job, totais e arquivos íntegros correspondem. Importação local não é rotulada como download.
- Histórico consulta os registros originadores de F005–F007. Snapshots de título preservam a identidade de importações/exports depois de remover mangá e capítulo.
- Remoção grava plano/itens antes de alterações, enumera contagens e paths, remove arquivos selecionados um a um e exige hash/containment. Arquivos não escolhidos ficam rastreados em **Arquivos sem vínculo**; podem ser removidos depois com confirmação própria.
- Migração `0006_library` adiciona favoritos, chaves de pesquisa, preferências, snapshots de identidade e diário de exclusão. `PRAGMA foreign_key_check` permanece sem violações.
- Testes focados: **24 passed**, incluindo busca em 10.000 mangás/100.000 capítulos com o limite `<500 ms`, restart, exclusão cancelada/confirmada, arquivo compartilhado/alterado, preservação de histórico, UI e teste de integração real F006→EPUB F007 com dados de fixture locais.
- Regressão completa: `uv run --locked --python 3.12 pytest tests -q` — **230 passed em 60,33s**. Testes de startup desktop isolados — **2 passed**. Ruff — **All checks passed**. MyPy — **117 source files, no issues**.
- As fixtures são carregadas somente nos testes. `examples/demo-import` oferece imagens geométricas sintéticas que a pessoa usuária importa explicitamente; elas não são copiadas para o perfil na inicialização.
- Comando para iniciar: `uv run --locked --python 3.12 manga-to-kindle` após `uv sync --locked --python 3.12`.

### Critérios de aceitação para validação manual

- No Windows 10/11, validar layout, foco/teclado, rótulos acessíveis, filtros, histórico, temas claro/escuro e estado vazio.
- Importar imagens de `examples/demo-import/pasta` para destino descartável; buscar com e sem acento, favoritar, reiniciar e confirmar disponibilidade **Importado localmente**.
- Exportar localmente EPUB/CBZ e verificar que Biblioteca/Historico mostram o resultado. A validação não deve sugerir compatibilidade com leitor físico que não tenha sido observada.
- Abrir prévia de remoção e cancelar; conferir que registro e arquivos não mudaram. Confirmar somente os registros e ver arquivos em **Arquivos sem vínculo**; depois excluir um único arquivo escolhido e confirmar preservação dos demais e da origem.
- Conferir que arquivos ausentes/alterados e compartilhados ficam protegidos, que caminho externo de original não pode ser selecionado e que saída de export só é elegível com hash registrado ainda válido.
- Usar PC Windows representativo para conferir a responsividade visual. A medição de 110 mil linhas passa automaticamente, mas não substitui a conferência no perfil real.

**Disponível para teste**: busca, filtros, favoritos, histórico, estado local de páginas, revisão de arquivos sem vínculo e exclusão explicitamente confirmada. **Não implementado/bloqueado**: download real F005 (sem fonte autorizada), atualização remota F010 (sem fonte autorizada) e distribuição instalável F012 (gates de release).

O roteiro completo está em [quickstart F008](008-local-library/quickstart.md).

## F009 — Envio ao Kindle

**Estado**: implementação local concluída e conectada à aplicação. O fluxo padrão abre a pasta de EPUB e a página oficial após clique; o fluxo SMTP é opcional, usa TLS validado e o Gerenciador de Credenciais do Windows, exige consentimento por tentativa e registra apenas o resultado observável do servidor. A aceitação SMTP não comprova entrega ao Kindle. Nenhum envio a conta Amazon, SMTP público ou aparelho real foi realizado.

### Funcionalidades e evidências

- A tela foi adicionada à navegação e recebe as exportações EPUB reais F007. Caminhos, tamanho e checksum são conferidos antes de abrir ou preparar uma transferência.
- A migração `0007_transfers` registra um perfil sem segredo e tentativas com destino mascarado. O cofre Win32 não exige dependência extra; um round-trip temporário real no Windows foi validado e a credencial removida.
- A aplicação monta MIME com os bytes exatos do EPUB, usa STARTTLS ou TLS implícito com validação de certificado e hostname, faz teste de conexão explícito sem submeter envelope e não retenta resultado desconhecido.
- Testes focados: **50 passed** em dois comandos (41 domínio/aplicação/infraestrutura/segurança/SMTP e 9 UI/regressão de exportação/navegação). A integração SMTP criou um EPUB pelo pipeline F006→F007 e usou servidor TLS real de loopback; incluiu aceite, rejeição temporária/permanente, timeout, TLS implícito, certificado inválido, teste sem MAIL/RCPT/DATA e desconexão após DATA.
- Um aborto nativo do Qt no primeiro agrupamento de testes foi reproduzido e corrigido: os testes da view agora aguardam o término efetivo do worker e a liberação da thread antes da próxima view. Os grupos isolados passaram sem warning.
- Regressão completa após F009: `uv run --locked --python 3.12 pytest tests -q` — **276 passed em 77,36s**. Ruff — **All checks passed**. MyPy — **133 source files, no issues**.
- A inicialização real pelo ponto de entrada `main()` foi executada em modo Qt offscreen com diretório temporário isolado. A migração `0007_transfers` foi aplicada, a composição SMTP foi conectada à janela e o shutdown terminou normalmente; nenhum dado do perfil real foi alterado.
- Round-trip temporário da API real Win32 Credential Manager passou; a credencial criada pela verificação foi removida.
- Comando para iniciar: `uv run --locked --python 3.12 manga-to-kindle` após `uv sync --locked --python 3.12`.

### Critérios para validação manual

- No Windows 10/11, verificar navegação por teclado/leitor de tela, foco, contraste, controles e mensagens de falha independentes ao abrir pasta e navegador.
- Importar explicitamente as imagens sintéticas de `examples/demo-import/pasta` para um destino descartável e exportar um EPUB em outra pasta temporária; nenhum exemplo é carregado automaticamente.
- Conferir que o perfil não conecta ao salvar; testar conexão em servidor próprio com TLS válido e verificar ausência de `MAIL`, `RCPT` e `DATA`.
- Se testar envio pela UI, usar EPUB sintético e somente conta/destino descartável controlados, confirmar os dados exatos no diálogo e cada autorização. Aceite precisa continuar rotulado como **Aceito pelo servidor SMTP — entrega ao Kindle não confirmada**.
- Alterar/remover o arquivo exportado e confirmar que a validação bloqueia o fluxo; reiniciar e conferir histórico mascarado sem reenvio automático.
- Confirmar no Gerenciador de Credenciais que a senha não aparece na configuração, banco, histórico, campos após salvar ou logs; confirmar que indisponibilidade do cofre desabilita SMTP e mantém o fluxo manual.

### Disponível e ainda pendente

- Disponível: ação manual, SMTP opt-in para um EPUB por destinatário, perfil e teste de conexão explícitos, cofre Windows, confirmação por tentativa, verificação de checksum, estados de aceite/rejeição/desconhecido, histórico persistente sem destinatário completo e sem retry automático.
- Pendente: validação visual/manual em máquina Windows representativa; confirmação de endereço/remetente pela pessoa usuária; compatibilidade do EPUB em Kindle físico e entrega/ingestão pela Amazon, que o aplicativo não observa; F010 e F012 seguem dependentes dos gates descritos nas respectivas specs.

O roteiro de execução e aceitação está em [quickstart F009](009-kindle-send/quickstart.md).

## F010 — Atualização de capítulos

**Estado**: a infraestrutura local de F010 está implementada: identidade estável de capítulo, reconciliação atômica, linha de base, histórico, preferências por mangá, avisos locais persistentes, controles de opt-in e scheduler restrito ao ciclo de vida do aplicativo. O refresh real e o monitoramento continuam bloqueados até um provedor registrado apresentar autorização para consulta de metadados, identidade estável e limites documentados e revisados. Nenhuma fonte no checkout satisfaz esse gate; a fixture não habilita consulta nem gera evidência de integração remota.

**Disponível para teste**: a tela Atualizações exibe o estado de forma segura e mantém as ações remotas desabilitadas com a fixture; a camada local persiste preferências/histórico/avisos, aplica a baseline e reconcilia apenas IDs estáveis. Testes de contrato isolados verificam esses comportamentos e as barreiras, sem afirmar que existe fonte real integrada. A tela não inicia jobs de download, exportação ou envio.

**Ainda indisponível**: refresh manual/periódico de fonte real e avisos de novidades obtidos remotamente. O gate exige termos oficiais e escopo aprovado para metadados, identificação estável, limite agregado, `Retry-After` e intervalo mínimo confirmados. Não use fixture ou transporte simulado como evidência de atualização concluída.

**Validação**: o roteiro focado F010 (`pytest` nos seis arquivos de domínio/aplicação/integração/UI listados no quickstart) passou com **27 testes em 5,40s**; o smoke de startup/navegação passou com **3 testes em 1,59s**. A regressão após a correção para recarregar o estado ao entrar na tela passou com `uv run --locked --python 3.12 pytest tests -vv`: **350 passed em 114,11s**. Ruff concluiu com `All checks passed`; MyPy concluiu com `Success: no issues found in 151 source files`. No executável Windows, a validação visual com perfil temporário carregou a fixture apenas por ação explícita, exibiu o status na tela Atualizações após navegação e reinício e manteve Downloads sem fonte autorizada. Isso valida apresentação/persistência local, não atualização remota. Os critérios manuais para fonte elegível seguem pendentes em [quickstart F010](010-chapter-updates/quickstart.md).

## F011 — Configurações e perfis

**Estado**: implementação local concluída e integrada ao pipeline de importação F006 e exportação F007. Perfis, preferências de processamento/recursos, pastas e cache persistem no banco local; restauração padrão exige confirmação e preserva biblioteca, exports, perfis customizados e referência do cofre.

### Funcionalidades e evidências

- Perfis internos Básico 8ª/10ª e Paperwhite 10ª, duplicação/editabilidade de perfis personalizados, dimensões variáveis persistidas e direção de leitura aplicada a novas importações/exports.
- Preferências de concorrência, pastas locais independentes, política de retenção e limite do cache, tema e restauração sem perda de conteúdo.
- Migrações `0008_settings` e `0009_profile_dimensions`; downgrade é recusado quando apagaria dimensões de páginas fora de 600×800.
- Demonstrações geométricas permanecem em `examples/demo-import` e só são importadas após escolha explícita. Nenhuma é copiada ao perfil na inicialização.
- Regressão completa após F011: `uv run --locked --python 3.12 pytest tests -vv` — **299 passed em 96,16s**. Ruff — **All checks passed**. MyPy — **Success: no issues found in 140 source files**.
- Inicialização composta em perfil temporário aplicou Paperwhite às telas F006/F007, leu/salvou preferências e encerrou sem alterar o perfil real.
- Comando exato para iniciar: `uv run --locked --python 3.12 manga-to-kindle` após `uv sync --locked --python 3.12`.

### Critérios de aceitação para validação manual

- No Windows 10/11, revisar acessibilidade, contraste/tema, navegação, mensagens e redimensionamento da área de Configurações.
- Conferir os perfis e as informações de hardware junto às fontes oficiais documentadas na spec; confirmar que a UI não promete compatibilidade física.
- Importar explicitamente imagens sintéticas em perfil descartável Paperwhite e verificar dimensões, snapshots e bytes originais; exportar EPUB/CBZ e abrir em leitor local.
- Verificar validação de pastas, confirmação/reset, cache vazio e a preservação de dados reais. Nenhuma fixture de cache elegível é criada para simular produção.

Roteiro, comandos, funcionalidades disponíveis/ausentes e critérios manuais estão em [quickstart F011](011-settings-profiles/quickstart.md).

## F012 — Distribuição Windows

**Estado**: implementação local do bundle `onedir` e ciclo do instalador disponível. O marco de aplicativo com instalador foi atingido para validação local no Windows 10 x64; não existe release aprovada nem matriz de suporte declarada.

### Evidências e testes

- Build local após F007/KCC executado no Windows 10 x64 build 19045 com Python 3.12.16 e PyInstaller 6.22.3 usando somente dependências de produção/build: `uv sync --locked --python 3.12 --no-default-groups --group build`; `uv run --locked --python 3.12 --no-default-groups --group build pyinstaller --clean --noconfirm packaging/pyinstaller/MangaToKindle.spec` — concluída.
- **Build de snapshot limpo**: `M2K_RUN_CLEAN_BUILD_TEST=1 uv run --locked --no-sync --python 3.12 pytest tests/packaging/test_release_from_clean_checkout.py -m release -q` — **1 passed em 104,61s**. O teste copiou os inputs versionados/atuais para pasta temporária sem `.git`, `.venv`, `dist` ou `build`, resolveu lock apenas com dependências de produção/build e produziu `MangaToKindle.exe`. Isso não é um build de commit limpo nem valida uma VM sem ferramentas de desenvolvimento.
- **Notices/atestação**: `tools/release/manifest.py` valida notices UTF-8 declarados e hashes; `tools/release/attestation.py` liga hash do ZIP e do manifest a `pending/passed/failed`, recusa ZIP corrompido/caminhos inseguros e, se a revisão for marcada como aprovada, exige notices presentes dentro do próprio artefato. Testes focados: **16 passed** em `test_dependency_licenses.py`, `test_release_manifest.py` e `test_release_attestation.py`; Ruff passou e MyPy passou nos dois módulos de release.
- Entry point PyInstaller chama `main()`; o bundle/instalador abriu em perfil isolado e aplicou `0011_mobi_export_artifacts`. Migrações são empacotadas em `_internal`; o executável KCC continua fora do bundle.
- Pacote local atual: `dist/local-release-draft/MangaToKindle-0.1.0-windows-x64-local-20261126-200905.zip`; SHA-256 `7bcc64183cc78ab5737e98e4bae8cb87817d0047d35a355d30c05094578a50c7` (**63.424.876 bytes**). O bundle tem 263 arquivos e 149.835.697 bytes. O pacote de validação inclui scripts PowerShell, aviso local, SBOM CycloneDX, candidatos de licença e inventário de arquivos como sidecars; KCC não está incluído.
- O SBOM atual tem 24 componentes; há metadata candidata encontrada para 23 e `macholib==1.16.4` segue ausente no host. As 24 revisões continuam `pending`; metadata não aprova licenças. O inventário real do `onedir` enumera 263 arquivos e 149.835.697 bytes com caminhos relativos e SHA-256, mas não mapeia a proveniência dos binários Qt nem determina suas licenças. T001/T017/T018/T023 seguem abertas até inventário/proveniência, notices completos, manifest do artefato e revisão humana.
- O instalador valida caminhos/links no ZIP e extrai por fluxo .NET seguro, instala por staging, preserva a versão anterior e restaura a versão anterior em falha após publicação. A remoção valida marcador/registro, repete até seis tentativas espaçadas para bloqueios de arquivo e só apaga atalho/registro após remover a pasta; os dados locais permanecem fora da instalação.
- Testes F012 já executados: `uv run --locked --python 3.12 pytest tests/packaging -q` — **24 passed em 23,16s** (antes da adição do teste lento; ele passa separadamente em 104,61s). Incluem startup real do bundle até `0011_mobi_export_artifacts`, lifecycle do ZIP atualizado em perfil descartável, instalação/upgrade/rollback, remoção e preservação do dado sentinela.
- Regressão completa final: `uv run --locked --python 3.12 pytest tests -q` com `M2K_KCC_EXE` apontando para a CLI oficial real — **363 passed em 133,91s**. Ruff (`src/manga_to_kindle tests tools`): **All checks passed**. MyPy (`src/manga_to_kindle tools/release/bundle_inventory.py tools/release/license_inventory.py tools/release/manifest.py`): **Success: no issues found in 153 source files**. `git diff --check` passou após as atualizações documentais; Git exibiu somente avisos de normalização LF/CRLF do checkout Windows.
- Uma regressão anterior falhou ao apagar `MangaToKindle.exe` no Windows com `UnauthorizedAccessException`, apesar do processo ter encerrado. O desinstalador recebeu tentativas limitadas e o teste end-to-end, a suíte F012 e a regressão completa passaram após a alteração; não foi possível determinar qual componente do Windows manteve o bloqueio.
- A raiz `MANGA_TO_KINDLE_DATA_ROOT` foi adicionada como override absoluto para smoke/QA isolado; sem ela, o aplicativo continua usando `QStandardPaths.AppLocalDataLocation`.
- **Smoke do rebuild**: o executável e o ZIP instalável abriram em perfis temporários e aplicaram `0011_mobi_export_artifacts`; testes de packaging passaram. Nenhum perfil real foi migrado pelos smokes.
- **Ocorrência de teste**: a primeira regressão completa usou bundle/ZIP anteriores (`0010`) enquanto os testes já esperavam `0011`; 361 testes passaram e os dois smokes F012 falharam por artefato obsoleto. Depois do rebuild/empacotamento, os 24 testes F012 e a regressão final de 363 passaram. Ao executar lint e pytest em paralelo, dois processos `uv run` também disputaram a atualização do mesmo entry point Windows; as verificações seriais com `--no-sync` passaram, e o teste de build isolado passou.
- Comando exato para iniciar pelo checkout: `uv run --locked --python 3.12 manga-to-kindle` após `uv sync --locked --python 3.12`.

### Critérios de aceitação manual pendentes

- Windows 10 e 11 limpos em cada par de arquitetura aprovado, sem Python/uv/Qt, verificando abertura, versão, ícone, funções e diretórios de dados.
- Atualização com banco e biblioteca sintéticos reais para o app, comparação de IDs/checksums e falha de migração; permissões, espaço insuficiente, arquivos em uso e cancelamento.
- Desinstalação/reinstalação por usuário com verificação de atalhos/registro e preservação de biblioteca, exports, originais e configurações.
- Aprovar matriz de arquitetura, revisar licenças de cada componente/notices, inspecionar SmartScreen/assinatura e anexar evidências/hashes à checklist.

### Disponível e ainda não disponível

- Disponível: build e ZIP local, instalação/atualização/remoção por usuário, preservação dos dados, fallback da instalação e startup testado do pacote real no perfil QA.
- Ainda indisponível: release aprovada, suporte x64/ARM64/x86 declarado, builds/VMs limpas Windows 10/11, assinatura digital e notices completos. Inno Setup, KCC e navegador não estão no bundle.

Consulte o [quickstart F012](012-windows-distribution/quickstart.md) e a [checklist de release](012-windows-distribution/checklists/release.md) para os comandos e critérios. Nenhuma validação manual pendente foi marcada como concluída.

## Funcionalidades disponíveis para teste

- F001: bootstrap, configuração, caminhos de usuário, banco local e encerramento seguro.
- F002: protótipo desktop navegável, atalhos, navegação por teclado e tema.
- F003: consulta e recusa de fonte sem rede, com fixture explicitamente fictícia.
- F004: consulta offline, metadados opcionais, ordenação, seleção individual/por intervalo e atualização recuperável.
- F005: fila persistida, controles, retry, integridade e recuperação verificados com transporte isolado nos testes; no aplicativo, apenas a tela e a barreira sem fonte estão disponíveis. Não há download real.
- F006: importação de pasta/CBZ autorizada, prévia 600×800, ordenação, processamento, cancelamento e recuperação. Dados de demonstração sintéticos disponíveis em `examples/demo-import`.
- F007: exportação local EPUB/CBZ nativa e MOBI via KCC 13.0.4 nos dois perfis verificados; critérios físicos pendentes no [quickstart F007](007-epub-kcc-export/quickstart.md).
- F008: busca/filtros/favoritos, disponibilidade verificada, histórico, migração e exclusão por escopo confirmado; critérios no [quickstart F008](008-local-library/quickstart.md).
- F009: abertura manual e SMTP TLS opt-in com confirmação e histórico; critérios no [quickstart F009](009-kindle-send/quickstart.md). Entrega ao Kindle não é verificada.
- F010: tela de estado, preferências/histórico/avisos locais, reconciliação por identidade estável e scheduler opt-in condicionado à política já estão implementados; a fixture permanece identificada e não habilita consulta. A integração remota segue bloqueada sem provedor autorizado. Detalhes em [quickstart F010](010-chapter-updates/quickstart.md).
- F011: perfis e preferências persistentes ligados a F006/F007, pastas/recursos e restauração sem perda; critérios em [quickstart F011](011-settings-profiles/quickstart.md).
- F012: bundle e instalador PowerShell reais em rascunho local; release aguarda matriz, revisão de licenças/notices e VMs limpas. Consulte o [quickstart F012](012-windows-distribution/quickstart.md).

O download real F005 e a atualização remota F010 continuam bloqueados enquanto não houver fonte autorizada. Nenhum transporte de teste é evidência desses fluxos. A distribuição F012 só pode ser aprovada depois da matriz, revisão de licenças e execução de instalação/upgrade/desinstalação em Windows limpo.

## Ainda não implementado ou bloqueado

- F005: primeiro download real. A fila local e seus controles foram implementados; a fonte externa permanece bloqueada até haver evidência verificável de autorização compatível com o uso local pretendido.
- F010: atualização remota, monitoramento efetivo e avisos derivados de catálogo consultado, dependentes de fonte/capacidade autorizadas com IDs e limites documentados. A infraestrutura local correspondente já está disponível para revisão e teste automatizado.
- F012: aprovação e publicação da distribuição Windows; implementação local do bundle/instalador já está disponível, mas arquitetura, licenças/notices e VMs limpas continuam como gates.

Não se deve usar as operações simuladas das telas atuais como evidência de conclusão desses fluxos.

## Comando para iniciar

No PowerShell, após `uv sync --locked --python 3.12`, o comando exato é:

```powershell
uv run --locked --python 3.12 manga-to-kindle
```

## Registro de ferramentas

O Project Tasks MCP não conseguiu associar este checkout a um projeto (`resolve_project_context: not_found`); nenhum registro remoto foi alterado. O andamento está registrado nos `tasks.md` locais e neste checkpoint.

O hook opcional `speckit.git.commit` não foi executado, conforme a instrução do `AGENTS.md` para não criar commits nem rodar hooks automaticamente.
