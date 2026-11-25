# Implementação contínua — Manga to Kindle

## Estado atual

- **Atualizado em**: 2026-11-25.
- **Feature em andamento**: F003 — Provedores extensíveis.
- **Tarefa atual**: F003:T001 — implementação local offline; fonte real permanece bloqueada sem autorização verificável.
- **Tarefas concluídas**: F001:T001–T020; validação anterior: 28 testes, Ruff aprovado, MyPy aprovado. F001 já tem seus 20 marcadores locais concluídos.
- **Próxima tarefa executável**: F003:T001 local, usando fixtures/offline e preservando o gate de fonte real.
- **MCP Project Tasks**: reconectado; projeto `cb1f3d9b-f17c-4080-8c32-27aca6349b87` confirmado e 12 features/F001–F002:T001–T018 existentes localizados. Registros remotos ainda pendentes; sincronização usará IDs existentes e respeitará dependências, sem duplicação.
- **Validações manuais pendentes F001 (`MANUAL_VALIDATION_PENDING`)**: abertura visual manual; instalação limpa em Windows 10/11; dez ciclos manuais de interface. Equivalentes automatizáveis executados na suíte Qt/integração.

## Progresso por feature

| Feature | Estado | Tarefas locais | Dependências/gates | Pendências e riscos |
|---|---|---:|---|---|
| F001 Fundação | COMPLETED | 20/20 | Nenhuma | `MANUAL_VALIDATION_PENDING` listado acima. |
| F002 Interface desktop | COMPLETED (automated) | 18/18 | F001 concluída | Validação visual manual em Windows 10/11 pendente (`MANUAL_VALIDATION_PENDING`). |
| F003 Provedores | PENDING | 0 | F001–F002 | Sem fonte real autorizada documentada: fixtures offline somente. |
| F004 Catálogo | PENDING | 0 | F001–F003 | Consultas reais herdam o gate de fonte; fixtures determinísticas. |
| F005 Downloads | PENDING | 0 | F001–F004 | Sem tráfego real até existir fonte autorizada; transporte fake. |
| F006 Imagens | PENDING | 0 | F001–F005 | Validar limites de extração/decodificação e preservar originais. |
| F007 EPUB/KCC | PENDING | 0 | F001–F006 | Verificar licença/API/CLI instalada; sem afirmar compatibilidade fixa ou executar KCC não verificado. |
| F008 Biblioteca local | PENDING | 0 | F001–F007 | Acrescentar migração ao runner único; exclusão com escopo/consentimento. |
| F009 Envio Kindle | PENDING | 0 | F001, F002, F007, F008 | Abrir Send to Kindle/pasta como padrão; SMTP real não autorizado. |
| F010 Atualizações | PENDING | 0 | F001–F005, F008 | Consultas reais aguardam fonte autorizada; sem download/envio automático. |
| F011 Configurações/perfis | PENDING | 0 | F001, F002, F005–F008 | Usar dados verificáveis; validar preferências com migrações. |
| F012 Distribuição Windows | PENDING | 0 | F001–F011 | Baseline/matriz de arquiteturas, licenças e execução em Windows limpo ainda precisam de evidência. |

## Histórico de execução

### Retomada autorizada — 2026-11-25

- A pessoa usuária autorizou expressamente F002–F012, incluindo F002, F007 e F012 anteriormente impedidas por autorização. Isso não remove gates técnicos, legais ou de dependência.
- Lidas a constituição, `AGENTS.md`, matriz de dependências, F002 `spec.md`, `plan.md`, `tasks.md`, `contracts/ui-boundary.md`, `data-model.md` e checklist. F002 depende somente da F001 concluída; checklist de requisitos da F002 está 16/16 marcada. Não foram alterados requisitos nem checklists.
- O checkout tinha F001 implementada; F002 foi entregue com cinco áreas Qt, seleção múltipla, temas, acessibilidade e demonstrações locais. A configuração/lock já incluíam PySide6; nenhuma dependência nova foi necessária.
- F002:T001 concluída: PySide6 já está configurada em `pyproject.toml` e resolvida no `uv.lock`; a sincronização travada e o teste de inicialização F001 confirmam o runtime disponível.
- F002 T001–T018 foram marcadas concluídas localmente após os artefatos e verificações correspondentes.

### F002 concluída — 2026-11-25

- Implementadas as cinco áreas da interface, tema claro/escuro persistido, atalhos e seleção múltipla; catálogo, downloads e conversão permanecem demonstrações offline claramente identificadas.
- Adicionado teste de composição com ciclo de vida F001. Testes combinados: **50 passaram**; Ruff aprovado; MyPy aprovado em 49 arquivos de origem. PySide6 resolvido: **6.12.0**; nenhuma dependência nova.
- A validação visual manual em Windows 10/11 permanece pendente; não declarar prontidão de release com base apenas no modo offscreen.
- Checklists de requisitos permaneceram somente leitura. O MCP voltou a responder e confirmou os registros existentes; a sincronização remota seguirá as dependências e as evidências, sem criar duplicatas.
