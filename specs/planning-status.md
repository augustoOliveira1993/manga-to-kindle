# Progresso do Planejamento — F001–F012

**Data**: 2026-11-25 | **Ordem**: numérica, respeitando dependências. `COMPLETED` significa artefatos de planejamento consistentes; não significa implementação nem liberação de gates.

| ID | Feature | Spec | Dependências | Status | Artefatos planejados | Pendências e riscos |
|---|---|---|---|---|---|---|
| F001 | Fundação | `001-app-foundation` | — | COMPLETED | plan, research, model, contracts, quickstart | Sem `pyproject.toml`/lock até implementar; escolher e resolver versões. |
| F002 | Interface desktop | `002-desktop-interface` | F001 | COMPLETED | plan, research, model, contracts, quickstart | Nenhum; Qt só após base F001. |
| F003 | Provedores extensíveis | `003-extensible-providers` | F001, F002 | COMPLETED | plan, research, model, contracts, quickstart | `B003-REAL-SOURCE`: fixtures apenas; risco SSRF/DNS/redirect. |
| F004 | Catálogo e capítulos | `004-catalog-chapters` | F001–F003 | COMPLETED | plan, research, model, contracts, quickstart | Consulta real bloqueada por B003; catálogo/seleção via fixtures. |
| F005 | Downloads | `005-download-queue` | F001–F004 | COMPLETED | plan, research, model, contracts, quickstart | B003 impede tráfego real; staging/atomicidade e concorrência 2. |
| F006 | Importação e imagens | `006-image-import-processing` | F001–F005 (F003 somente como limite legal/privacidade; sem rede) | COMPLETED | plan, research, model, contracts, quickstart | Limites CBZ/imagem e compatibilidade WEBP no ambiente Windows. |
| F007 | EPUB/KCC | `007-epub-kcc-export` | F001–F006 | COMPLETED | plan, research, model, contracts, quickstart | Gated: licença/fixed-layout EbookLib; rede KCC; capacidade por versão. |
| F008 | Biblioteca local | `008-local-library` | F001–F007 | COMPLETED | plan, research, model, contracts, quickstart | Migrações SQLite e integridade/recuperação de arquivos. |
| F009 | Envio ao Kindle | `009-kindle-send` | F001, F002, F007, F008 | COMPLETED | plan, research, model, contracts, quickstart | Cofre Windows e configuração SMTP; autorização por envio. |
| F010 | Atualização de capítulos | `010-chapter-updates` | F001–F005, F008 | COMPLETED | plan, research, model, contracts, quickstart | B003 impede provedor real; monitoramento opt-in e sem auto download. |
| F011 | Configurações/perfis | `011-settings-profiles` | F001, F002, F005–F008 | COMPLETED | plan, research, model, contracts, quickstart | Revalidar dimensões/modelos em fonte oficial antes de implementar. |
| F012 | Distribuição Windows | `012-windows-distribution` | F001–F011 | COMPLETED | plano preexistente atualizado; pesquisa/modelo/contratos/quickstart/checklists preservados | `B012-ARCH-MATRIX` sem resposta humana; `B012-IMPLEMENTATION-BASELINE`; license gate Inno Setup. |

## Dependências de implementação consolidadas

1. F001 → F002 → F003 → F004 → F005 → F006 → F007 → F008.
2. F006 necessita das identidades/ordem de F004/F005; F007 depende de F001–F006.
3. F001 é proprietário do engine e mecanismo de migrations; features persistentes acrescentam suas próprias revisões ao introduzir seus dados. F008 consolida entidades/consultas após F001–F007; não recria modelos nem migrations aplicadas.
4. F009 depende de F007/F008; F010 depende de F003/F004/F005/F008; F011 depende de F001/F002/F005/F006/F007/F008.
5. F012 depende de F001–F011 e é a última etapa de build/release.

## Decisões/premissas

- Constituição lida em `.specify/memory/constitution.md`; sem emendas.
- Ponteiro do Spec Kit permanece em F012. Esqueletos dos planos foram gerados pelo `setup-plan.ps1 -Json` oficial com `SPECIFY_FEATURE_NO_PERSIST=1`.
- Não havia planos em F001–F011. O plano F012 já existente foi mantido e recebeu apenas correção de rastreabilidade para RF-030; os demais artefatos F012 e checklists foram preservados.
- Não há diretório `docs/roadmap.md` neste checkout; este grafo é derivado das seções Dependências das 12 specs e deve ser comparado com roadmap caso venha a existir.
- Uma pergunta de clarificação de F012 sobre pares Windows/arquitetura não recebeu resposta. Não foi presumida arquitetura; somente a matriz final e a publicação permanecem bloqueadas.
- Fontes reais, capacidades e licenças não foram concedidas por este planejamento. Fixtures não são apresentadas como integrações de produção.

## Revisão integrada

- Todos os módulos compartilham camadas/contratos e fonte de verdade em [architecture-plan.md](architecture-plan.md).
- Dependências são acíclicas conforme a ordem acima; F008 consolida persistência sem duplicar schema inicial de F001.
- Operações externas ou de arquivo usam workers; mensagens/logs sanitizados; livros permanecem locais salvo consentimento explícito.
- Gates bloqueiam apenas integrações/saídas que dependem da decisão; as features locais/fakes continuam planejáveis.
- `COMPLETED` para F001–F012 indica plano criado/preservado e revisado, não aceite funcional, testes executados ou gate removido.
