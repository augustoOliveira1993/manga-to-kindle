# Plano global de tarefas — Manga to Kindle

Este documento coordena os `tasks.md` das features F001–F012. Os arquivos locais por feature são a fonte de verdade das tarefas; esta matriz registra precedências, componentes compartilhados e gates sem duplicar tarefas.

## Ordem de implementação e dependências

| Ordem | Feature | Diretório | Dependências | Saída compartilhada que desbloqueia |
|---|---|---|---|---|
| 1 | F001 — Fundação | `specs/001-app-foundation` | — | Bootstrap, settings/paths, contratos de domínio, SQLite/Alembic único, logging e lifecycle |
| 2 | F002 — Interface desktop | `specs/002-desktop-interface` | F001 | Casca PySide6, estados de UI e worker/sinais/cancelamento |
| 3 | F003 — Provedores | `specs/003-extensible-providers` | F001, F002 | Provider registry, fixture offline, erros e política de URL segura |
| 4 | F004 — Catálogo | `specs/004-catalog-chapters` | F001–F003 | Consulta via providers, IDs de capítulos, ordenação e seleção |
| 5 | F005 — Downloads | `specs/005-download-queue` | F001–F004 | Fila persistente, transporte injetável, validação e progresso |
| 6 | F006 — Imagens | `specs/006-image-import-processing` | F001–F005 | Importação local/CBZ segura e pipeline de derivados |
| 7 | F007 — Exportação | `specs/007-epub-kcc-export` | F001–F006 | EPUB/CBZ local, adaptadores de conversão verificados |
| 8 | F008 — Biblioteca | `specs/008-local-library` | F001–F007 | Busca/histórico consolidado e semântica explícita de exclusão |
| 9 | F009 — Envio | `specs/009-kindle-send` | F001, F002, F007, F008 | Fluxo manual prioritário, SMTP opt-in e histórico |
| 10 | F010 — Atualizações | `specs/010-chapter-updates` | F001–F005, F008 | Refresh manual e monitoramento opt-in com IDs estáveis |
| 11 | F011 — Perfis | `specs/011-settings-profiles` | F001, F002, F005–F008 | Fonte única de preferências e perfis integrados |
| 12 | F012 — Distribuição | `specs/012-windows-distribution` | F001–F011 | Build/release Windows e lifecycle do instalador |

## Arquitetura compartilhada e prevenção de duplicação

- Domínio, aplicação, infraestrutura e apresentação são fronteiras comuns; UI delega toda operação potencialmente bloqueante para workers Qt com progresso, erro e cancelamento.
- F001 é dona do bootstrap, configuração/caminhos de usuário, logging, banco SQLite e runner Alembic. Features adicionam revisões ao runner único, sem engine ou migração paralelos.
- F003 é dona do contrato/registry de MangaProvider, da fixture offline, erros de provider e política central de URL externa. F004 consulta esses contratos; F005 não cria clientes/provider alternativos.
- F005 é dona de DownloadJob/fila, retry/rate-limit, transporte injetável e gravação temporária/atômica. F010 não agenda downloads.
- F006 preserva originais e é dona apenas do importador/pipeline de imagens; F007 exporta os derivados sem reprocessar origem. F008 consolida consultas e integridade sem duplicar lógica proprietária dos módulos.
- F009 não automatiza login nem envio padrão. F010 não baixa/envia. F011 fornece preferências aos consumidores. F012 apenas empacota paths de usuário, nunca é dona dos dados.

## Paralelização e caminho crítico

- Caminho crítico primário: `F001 → F002 → F003 → F004 → F005 → F006 → F007 → F008 → F011 → F012`.
- F009 pode começar após F007 e F008; F010 após F005 e F008. Assim, F009/F010 podem avançar em paralelo depois dos pré-requisitos, e F011 após F008/F005/F006/F007. F012 continua última.
- Dentro de uma feature, somente tarefas marcadas `[P]` podem ser paralelizadas; implementação de cada história depende dos testes/contratos precedentes indicados em seu `tasks.md`.
- Nenhum planejamento manda executar várias migrações concorrentes sobre o mesmo SQLite; contribuições de schema são sequenciais no runner compartilhado.

## Gates e riscos transversais

- **G-F003/F005/F010 — fonte real**: até que exista fonte com download autorizado, documentação verificável, termos/licenças e limites confirmados, validar apenas fixture/transporte fake. Sem bypass de DRM, CAPTCHA, autenticação ou controles de acesso.
- **G-F007 — conversão**: o writer EPUB usa biblioteca padrão e passou pelo EPUBCheck. A CLI oficial KCC 13.0.4 foi validada para MOBI com perfis K810 (600×800) e KPW34 (1072×1448); é selecionada por caminho, não empacotada e não instalada automaticamente. Sem promessa de compatibilidade Kindle/Send to Kindle; teste físico permanece pendente.
- **G-F009 — SMTP**: integração opcional requer cofre do sistema, destinatário autorizado e confirmação por tentativa; resultado de aceite nunca significa entrega.
- **G-F012 — release**: baseline do app e build local existem; não presumir matriz x86/x64/ARM64. Inno Setup, KCC e browser ficam condicionados a licença/requisitos. Windows limpo deve ser executado e documentado antes de release.
- Dados sempre ficam fora da instalação; operações mutáveis usam transações/staging/finalização atômica e recuperação; logging sem segredos ou conteúdo dos livros.

## Progresso de geração e sincronização

| Feature | Dependências | Status da geração | Tarefas | [P] | Testes | Já concluídas | Pendências de execução | MCP Project Tasks |
|---|---|---:|---:|---:|---:|---:|---|---|
| F001 | — | COMPLETED | 20 | 2 | 8 | 0 | Nenhuma para gerar tarefas | SYNCED (20/20) |
| F002 | F001 | COMPLETED | 18 | 2 | 8 | 0 | Nenhuma para gerar tarefas | SYNCED (18/18) |
| F003 | F001–F002 | COMPLETED | 18 | 2 | 7 | 0 | Fonte real autorizada bloqueada | SYNCED (18/18) |
| F004 | F001–F003 | COMPLETED | 20 | 2 | 8 | 0 | Fonte real autorizada bloqueada | SYNCED (20/20) |
| F005 | F001–F004 | COMPLETED | 26 | 2 | 11 | 0 | Fonte real autorizada bloqueada | SYNCED (26/26) |
| F006 | F001–F005 | COMPLETED | 24 | 2 | 12 | 0 | Nenhuma para gerar tarefas | SYNCED (24/24) |
| F007 | F001–F006 | COMPLETED | 24 | 2 | 10 | 0 | Compatibilidade física Kindle/Send to Kindle | SYNCED (24/24) |
| F008 | F001–F007 | COMPLETED | 22 | 2 | 10 | 0 | Nenhuma para gerar tarefas | SYNCED (22/22) |
| F009 | F001,F002,F007,F008 | COMPLETED | 24 | 2 | 11 | 0 | Cofre Windows antes de SMTP | SYNCED (24/24) |
| F010 | F001–F005,F008 | COMPLETED | 24 | 2 | 11 | 0 | Fonte real autorizada bloqueada | SYNCED (24/24) |
| F011 | F001,F002,F005–F008 | COMPLETED | 26 | 2 | 12 | 0 | Fontes documentadas para diferenças de hardware | SYNCED (26/26) |
| F012 | F001–F011 | COMPLETED | 25 | 2 | 9 | 0 | Baseline, matriz Windows e licenças | SYNCED (25/25) |

**Totais locais**: 12 features; 271 tarefas; 24 tarefas paralelizáveis; 117 tarefas de teste/checklist; 0 tarefas previamente concluídas. A contagem de testes identifica tarefas cujo resultado principal é teste/checklist verificável; subtarefas com validação secundária não são contadas novamente.

**Sincronização MCP**: projeto `cb1f3d9b-f17c-4080-8c32-27aca6349b87` (Manage To Kindle), repositório/área `backend` (`9b02703b-4ae7-4400-868a-ea4f73f91034`). Foram vinculadas 12 features e 271 tarefas pelos IDs `Fnnn:Tnnn`, com dependências por ID e um anexo `sdd-context.md` por tarefa. Todas permanecem pendentes; a verificação retornou 271 tarefas esperadas, sem IDs ausentes/duplicados, vínculos incorretos ou dependências inválidas.

## Validação consolidada

- Cobertura: cada história tem tarefas de teste antes de suas tarefas de implementação; os intervalos RF/RNF/CS são mapeados ao fim de cada `tasks.md`.
- Sequência: IDs T001…Tnn são únicos e crescentes dentro de cada feature. Referências cross-feature usam `Fnnn:Tnnn` sem redefinir entregáveis upstream.
- Regras comuns: sem tarefas de implementação para fonte real não aprovada; sem rede nas fixtures; sem envio automático; sem I/O bloqueante na UI; sem exclusão/desinstalação destrutiva por padrão.
- Status `COMPLETED` significa geração e revisão local dos planos de tarefas, não implementação das features nem aprovação dos gates acima.
