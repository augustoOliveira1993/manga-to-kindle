# Checkpoint de implementação — Manga to Kindle

Atualizado em 26/11/2026. Este checkpoint reúne as entregas locais, verificações executadas e critérios manuais pendentes. A ordem das features continua definida em [task-dependencies.md](task-dependencies.md).

## Estado dos marcos

| Marco | Estado |
|---|---|
| F002 — protótipo visual navegável | Atingido; navegação e telas base estão disponíveis. |
| F005 — primeiro download funcional | Pendente; a fila local está implementada, mas falta uma fonte com autorização verificável para habilitar o primeiro download real. |
| F006 — importação e processamento de imagens | Atingido para conteúdo local autorizado; processamento, persistência e recuperação estão implementados. A validação visual manual no Windows continua pendente. |
| F007 — MVP EPUB | Atingido: geração e validação estrutural local de EPUB/CBZ. KCC e validação em Kindle físico continuam pendentes. |
| F008 — Biblioteca Local | Atingido: consulta persistida, disponibilidade, histórico e remoção explícita implementados. A validação visual manual no Windows continua pendente. |
| F009 — envio ao Kindle | Não implementado. |
| F012 — instalador Windows | Não implementado. |

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

**Estado**: importação local de pastas e CBZ autorizados, prévia ordenável, perfil 600×800, recorte opcional e divisão manual de páginas duplas RTL/LTR implementados. O aplicativo permanece local: preserva originais, publica derivados separadamente e não acessa rede. A integração com preferências configuráveis de dispositivo continua dependente da F011; até lá, a F006 usa o perfil base Kindle Básico 10ª geração.

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

## F007 — Exportação local EPUB/CBZ

**Estado**: MVP atingido. O writer EPUB próprio usa a biblioteca padrão conforme autorização explícita da pessoa usuária; exportação local não envia arquivos nem inicia KCC. A compatibilidade com Kindle físico/Send to Kindle ainda não foi validada.

### Evidências e testes

- A F007 planeja a partir de páginas derivadas e metadados existentes, grava EPUB 3 fixed-layout ou CBZ na pasta escolhida e persiste estado/checksums no SQLite. O staging e a publicação atômica preservam arquivos com nomes conflitantes; cancelamento e falhas removem somente saídas parciais gerenciadas.
- Os testes focados F007 passaram: `41 passed`. Os testes de inicialização desktop isolada passaram: `2 passed`.
- A suíte completa passou após atualizar a asserção do aviso offline: `205 passed`. A regressão inclui inicialização, navegação, downloads, importação de imagens, EPUB/CBZ, validação de recursos, ausência de rede e testes de interface.
- Ruff: `All checks passed`. MyPy: `Success: no issues found in 111 source files`.
- Uma fixture EPUB 3 foi verificada com EPUBCheck 5.4.0: `0 fatal / 0 errors / 0 warnings / 0 infos`. Isso verifica a estrutura do pacote, não a compatibilidade num leitor físico.
- A inicialização desktop em perfil temporário é coberta por testes que compõem o controlador, janela e migrações. O comando de distribuição local permaneceu ativo em modo Qt offscreen por 8 segundos; o teste foi encerrado sem importar exemplos. A tentativa direta respeitou o caminho de dados do Windows já configurado (`QStandardPaths`), não o `LOCALAPPDATA` temporário; por isso a validação isolada e as verificações de inicialização usam `AppPaths` temporário nos testes. O banco existente já reportava a revisão `0005_export_artifacts` e a tabela de artefatos antes desta conferência; nenhum exemplo foi importado.
- Comando exato para iniciar (após sincronizar dependências): `uv run --locked --python 3.12 manga-to-kindle`.

### Critérios para validação manual

- No Windows 10/11, conferir rótulos, foco por teclado, rolagem, tema, diálogo de destino e atualização da lista após uma importação.
- Importar explicitamente `examples/demo-import/pasta` ou `demo.cbz` em um perfil temporário, exportar capítulo e volume em EPUB/CBZ, conferir ordem, sumário, RTL/LTR, limite/divisão, cancelamento e colisão de nomes. Os exemplos são sintéticos e nunca entram no perfil automaticamente.
- Abrir arquivos em leitores locais e anotar layout/capa/navegação. Para aceitação em dispositivo, registrar checksum, modelo/geração, firmware, rota USB ou Send to Kindle e resultado observado; essa verificação permanece pendente.
- Confirmar em dispositivo que os bytes originais continuam iguais e que arquivos já existentes não são substituídos sem confirmação.

### Disponível e ainda pendente

- Disponível: exportação EPUB 3 fixed-layout e CBZ de capítulos importados/processados, capa neutra quando ausente, metadados, navegação, ordem, RTL/LTR em EPUB, divisão por tamanho, validação interna, cancelamento, staging, publicação local e histórico SQLite.
- Pendente: adaptador KCC real (T017/T018) e compatibilidade Kindle/Send to Kindle validada fisicamente. A F008 integrou o histórico local. A tela não envia conteúdo.

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

**Disponível para teste**: busca, filtros, favoritos, histórico, estado local de páginas, revisão de arquivos sem vínculo e exclusão explicitamente confirmada. **Não implementado/bloqueado**: download real F005 (sem fonte autorizada), envio F009, atualizações F010, integração completa de perfis F011 e instalador F012.

O roteiro completo está em [quickstart F008](008-local-library/quickstart.md).

## Funcionalidades disponíveis para teste

- F001: bootstrap, configuração, caminhos de usuário, banco local e encerramento seguro.
- F002: protótipo desktop navegável, atalhos, navegação por teclado e tema.
- F003: consulta e recusa de fonte sem rede, com fixture explicitamente fictícia.
- F004: consulta offline, metadados opcionais, ordenação, seleção individual/por intervalo e atualização recuperável.
- F005: fila persistida, controles, retry, integridade e recuperação verificados com transporte isolado nos testes; no aplicativo, apenas a tela e a barreira sem fonte estão disponíveis. Não há download real.
- F006: importação de pasta/CBZ autorizada, prévia 600×800, ordenação, processamento, cancelamento e recuperação. Dados de demonstração sintéticos disponíveis em `examples/demo-import`.
- F007: exportação local EPUB/CBZ a partir dos derivados F006; detalhes e critérios no [quickstart F007](007-epub-kcc-export/quickstart.md).
- F008: busca/filtros/favoritos, disponibilidade verificada, histórico, migração e exclusão por escopo confirmado; critérios no [quickstart F008](008-local-library/quickstart.md).

O download real F005 continua bloqueado enquanto não houver fonte autorizada; nenhum transporte de teste é evidência de download funcional. Envio ao Kindle, atualização de capítulos e instalador continuam pendentes nas F009/F010/F012.

## Ainda não implementado ou bloqueado

- F005: primeiro download real. A fila local e seus controles foram implementados; a fonte externa permanece bloqueada até haver evidência verificável de autorização compatível com o uso local pretendido.
- F009: fluxo completo de envio ao Kindle.
- F010: atualizações de capítulos.
- F011: integração completa de perfis e preferências.
- F012: distribuição e instalador Windows.

Não se deve usar as operações simuladas das telas atuais como evidência de conclusão desses fluxos.

## Comando para iniciar

No PowerShell, após `uv sync --locked --python 3.12`, o comando exato é:

```powershell
uv run --locked --python 3.12 manga-to-kindle
```

## Registro de ferramentas

O Project Tasks MCP não conseguiu associar este checkout a um projeto (`resolve_project_context: not_found`); nenhum registro remoto foi alterado. O andamento está registrado nos `tasks.md` locais e neste checkpoint.

O hook opcional `speckit.git.commit` não foi executado, conforme a instrução do `AGENTS.md` para não criar commits nem rodar hooks automaticamente.
