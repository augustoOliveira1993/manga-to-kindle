# Plano de Implementação: F012 — Distribuição Windows

**Branch**: `012-windows-distribution` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Entrada**: Especificação da feature F012.

## Resumo

Empacotar o aplicativo desktop local para Windows 10/11 com PyInstaller, usando um bundle portátil `onedir` como saída-base e Inno Setup somente se a licença e o modelo de uso forem aprovados. O artefato deve registrar proveniência e dependências, preservar a raiz de dados do usuário em atualização e desinstalação e passar por instalação, upgrade e remoção em VMs limpas. O plano integra a aplicação e a persistência definidas por F001–F011; não redesenha nem substitui esses módulos.

## Contexto Técnico

**Linguagem/versão**: Python 3.12 ou superior; o pipeline de release deve fixar uma versão de manutenção e registrar o patch efetivamente utilizado.

**Dependências principais**:

- Runtime: PySide6; SQLAlchemy 2; Alembic para migrações versionadas; Pydantic v2 para validar os contratos de metadados/manifests onde houver entrada JSON.
- Funcionalidades anteriores: Pillow na feature de imagens; HTTPX/BeautifulSoup4 somente para provedores autorizados que os exijam; EbookLib continua bloqueado por `B007-EBOOKLIB-LICENSE`; KCC permanece instalação externa opcional conforme F007.
- Build: PyInstaller, em versão fixada no grupo de dependências de build e no lock.
- Desenvolvimento: uv, Ruff, MyPy e Pytest em grupos separados do runtime.
- Não incluir KCC, navegadores ou ferramentas de desenvolvimento no pacote padrão. Playwright, HTTPX e BeautifulSoup4 não são dependências desta feature.

Versões exatas não podem ser fixadas ainda: não existem `pyproject.toml`, `uv.lock` nem implementação neste checkout. O planejamento define a estratégia; a escolha e resolução das versões ocorrem quando F001–F011 fornecerem uma base instalável.

**Persistência**: SQLite sob a raiz de dados local estabelecida em F001/F008. SQLAlchemy 2 fornece mapeamento tipado; Alembic fornece revisões ordenadas e tabela de versão. PyInstaller e o instalador não alteram o banco. No primeiro início após upgrade, a aplicação cria e verifica backup antes de executar migrações.

**Testes**: Pytest para contratos, metadados, caminhos, proveniência, processo de upgrade e recuperação; Ruff e MyPy para o código do produto; VMs descartáveis limpas para Windows 10/11 em cada arquitetura aprovada. Testes em VM e release manual permanecem pendentes até existir build executável.

**Plataforma-alvo**: Windows 10/11. A arquitetura do processador é entrada obrigatória da matriz de release e permanece pendente (`B012-ARCH-MATRIX`); nenhum par não aprovado/testado pode ser anunciado.

**Tipo de projeto**: Aplicativo desktop local com uma camada de distribuição Windows.

**Metas de desempenho**: Não foram definidos limites numéricos novos. A janela deve continuar responsiva durante inicialização/migração e demais operações de disco; os critérios existentes da F002/F012 são preservados.

**Restrições**: Nenhuma rede no primeiro início, nenhum auto-update, nenhuma escrita de dados na pasta de instalação, nenhuma remoção implícita da biblioteca, nenhum segredo ou conteúdo de livro em manifests/logs, sem build cruzado do PyInstaller.

**Escopo**: Um produto desktop, artefato portátil `onedir`, possível instalador por usuário, dados locais já definidos nas features anteriores e documentação de release. Assinatura digital, canais automáticos de atualização, lojas e distribuição multiplataforma estão fora do escopo da spec.

## Checagem da Constituição

| Princípio/gate | Aplicação no plano | Situação |
|---|---|---|
| Camadas e dependências para dentro | Domínio sem PySide6/SQLAlchemy; casos de uso via portas; infraestrutura adapta banco/sistema; apresentação Qt é a fronteira de UI. F012 só adiciona o limite de build/distribuição. | Conforme |
| SOLID, KISS, YAGNI, tipagem | Tipos explícitos em portas, manifest e entidades; nenhuma lógica de domínio em hooks do empacotador; configuração concreta montada no composition root. | Conforme |
| UI responsiva, progresso e cancelamento | Migração e validação de dados executadas em worker Qt; sinais tipados/slots entregam estados ao thread da UI; cancelamento só em limites seguros da transação. O instalador pede encerramento gracioso. | Conforme |
| Dados locais, migrações, atomicidade e recuperação | Raiz de usuário separada da instalação; backup SQLite verificado antes de migração; atualização não apaga a cópia recuperável; desinstalação padrão preserva dados. | Conforme |
| Erros, logs, segurança e privacidade | Logs sem segredos/conteúdo; mensagens acionáveis; manifest contém apenas proveniência de build e dados de pacote, sem caminho pessoal do builder. | Conforme |
| Testes, documentação e dependências verificadas | Pytest/Ruff/MyPy; lock uv; inventário de licenças; README, AGENTS, avisos e checklist de release. | Conforme após implementação |
| Base anterior disponível | F012 depende de F001–F011, mas não há código, `pyproject.toml`, `uv.lock` ou build neste checkout. | **Gate bloqueado**: `B012-IMPLEMENTATION-BASELINE` |
| Matriz de arquitetura aprovada | Spec deixa x64/ARM64/x86 para decisão humana e exige teste por par Windows/arquitetura. | **Gate aberto**: `B012-ARCH-MATRIX` |
| Licenças e ferramentas opcionais | Inno Setup é opcional; EbookLib/KCC mantêm gates de F007; navegador não é empacotado. | **Gate de release**: revisão e evidência antes de incluir qualquer componente |

O plano documental pode ser concluído sem executar build. A implementação/release não pode declarar sucesso até os gates acima serem resolvidos. A matriz será um parâmetro do desenho dos manifestos e da checklist; este plano não escolhe arquitetura por inferência.

## Decisões de Arquitetura

1. **Aplicação existente continua dona dos dados.** O instalador só troca binários/atalhos; não importa modelos SQLAlchemy nem executa migrações diretamente.
2. **Migração ocorre no bootstrap da aplicação.** Um caso de uso de inicialização invoca uma porta de migrações implementada na infraestrutura Alembic/SQLAlchemy. Antes da mudança, cria backup local em diretório gerenciado, valida o arquivo e registra revisão de origem/destino. Falha mantém backup e impede uso normal até recuperação explícita.
3. **Migração não bloqueia a UI.** A aplicação exibe estado em português, progresso quando mensurável e resultado/erro; um worker de longa duração comunica-se por sinais/slots Qt. Cancelamento é permitido antes de uma etapa irreversível ou após conclusão/rollback da transação, nunca interrompendo uma gravação no meio.
4. **Bundle de uma pasta é a saída-base.** O `.spec` versionado é a fonte da configuração PyInstaller. O pacote portátil é arquivado para distribuição; Inno Setup pode consumi-lo quando sua licença e modo de uso forem aprovados. A escolha `onedir` facilita inspeção de DLLs, plugins Qt e arquivos de licença e corresponde ao padrão documentado do PyInstaller.
5. **Build Windows é nativa e explicitamente arquitetada.** Cada worker de release executa Windows e Python da arquitetura aprovada; não usa `--target-arch` como conversor cruzado. Build, manifesto e VM usam o mesmo par declarado.
6. **Dependências são por função, não por conveniência.** Runtime, grupos `dev` e `build` são separados. Dependências usadas por F003–F007 só entram no artefato se presentes no lock e necessárias ao caminho autorizado; extras opcionais não são copiados automaticamente.
7. **Proveniência tem duas visões.** Um manifest normalizado registra entradas/configuração/componentes; uma atestação por artefato registra o arquivo e seu SHA-256. Assim, a comparação de builds não esconde diferenças de bytes nem introduz campos variáveis na comparação dos insumos.

## Modelo de Dados e Migrações

Os dados de release são arquivos externos de distribuição, não tabelas do catálogo local. Ver [data-model.md](data-model.md) e os contratos em [contracts/](contracts/).

Para dados do aplicativo, `Manga`, `Chapter`, `Page`, `DownloadJob`, `DeviceProfile` e `Export` continuam modelos/entidades de F001 e features dependentes. SQLAlchemy 2 usa `DeclarativeBase`, `Mapped` e `mapped_column` em modelos de infraestrutura; objetos de domínio não herdam modelos ORM. Pydantic valida fronteiras JSON/configuração e não substitui entidades de domínio ou tabelas.

Alembic guarda as revisões versionadas; autogeração é apenas rascunho sujeito a revisão. Para upgrade, worker de bootstrap fecha sessões, faz backup com estratégia SQLite consistente, valida integridade, aplica revisões encadeadas e verifica a revisão final. Em falha, mantém backup original, captura erro sanitizado, não inicia serviços que dependem do schema e apresenta instrução de recuperação. Downgrade destrutivo automático não é estratégia de rollback; a recuperação preserva/repõe uma cópia compatível de forma explícita.

## Estratégia de Testes

- **Unidade**: validação de `ReleaseManifest`, semver, hashes, lista de componentes, licenças pendentes, seleção de arquitetura e transições da checklist; montagem de paths sem depender do diretório de instalação.
- **Integração**: build em fixture de app; inspeção do conteúdo do bundle e plugins Qt/PySide6; manifesto de dependências e avisos; abertura sem ambiente Python de desenvolvimento; ausência de rede no primeiro início.
- **Persistência/upgrade**: fixtures sintéticas SQLite com F001–F011; 10 ciclos de update; IDs/relacionamentos/preferências e SHA-256 de arquivos iguais; falha injetada antes/durante/depois da migração, backup preservado, disco cheio e processo aberto.
- **UI/worker**: janela responsiva durante bootstrap/migração, mensagens em pt-BR, sinais de progresso/erro/conclusão/cancelamento chegando à thread GUI e operações de cancelamento apenas em pontos seguros.
- **Instalação/desinstalação**: VMs descartáveis Windows 10/11 por arquitetura aprovada; usuário sem Python, uv, Qt ou ambiente de desenvolvimento; instalação padrão por usuário, upgrade, app aberto, cancelamento, desinstalação padrão e exclusão de dados com caminho/escopo confirmados.
- **Qualidade**: Pytest focado e suíte relevante, Ruff, MyPy, revisão do `.spec`, inspeção do `uv.lock`, inventário completo de licenças e aviso de terceiros.
- **Evidência de release**: versão da VM, imagem de build, arquitetura, commits, comandos, resultado, hashes e evidência anexados por item; item não executado fica “Pendente”. Não usar biblioteca ou credenciais reais.

Nenhum teste, build, lint ou typecheck foi executado nesta etapa de planejamento.

## Dependências e Gates

| Dependência | Uso planejado | Condição |
|---|---|---|
| Python 3.12+ e uv | Runtime de build, resolução e sincronização com lock. | Fixar patch compatível no início da implementação; `uv.lock` obrigatório. |
| PySide6 | UI, bootstrap, worker e sinais Qt definidos nas features anteriores. | Validar plugin/DLL no bundle em build real. |
| SQLAlchemy 2 + Alembic | Persistência SQLite e revisões da aplicação. | Alembic é a escolha do plano; alinhar detalhe de migration runner com F001 antes da implementação. |
| Pydantic v2 | Validação de manifest/entrada JSON e geração de JSON Schema quando houver fronteira serializada. | Manter fora do domínio puro; confirmar necessidade no lock do produto. |
| PyInstaller | Bundle Windows `onedir`. | Fixar versão e licença; executar build no Windows-alvo; nunca inventar hooks/hidden imports. |
| Ruff, MyPy, Pytest | Desenvolvimento, qualidade estática e testes. | Grupo dev, não empacotado. |
| Pillow | Processamento F006 e conversão de ícone se necessário. | Empacotar somente quando F006 e análise de dependências confirmarem uso. |
| EbookLib | Export EPUB F007. | Bloqueado por `B007-EBOOKLIB-LICENSE`. |
| KCC / navegador | Integrações opcionais conforme F007/F009. | Externos e ausentes do bundle padrão; sem instalação/download automático. |
| HTTPX / BeautifulSoup4 / Playwright | Provedores autorizados ou automação apenas quando a feature exigir. | Não necessários à F012; Playwright/browser fora do pacote. |
| Inno Setup | Instalador opcional para usuário. | Aprovação/licença para o modelo concreto antes de compilar ou redistribuir. |

## Estrutura do Projeto Planejada

```text
pyproject.toml
uv.lock
src/manga_to_kindle/
├── __main__.py                    # entrada e composição/injeção
├── domain/                         # entidades e regras sem frameworks
├── application/                    # casos de uso e portas tipadas
├── infrastructure/
│   ├── persistence/                # SQLAlchemy, SQLite e adapters Alembic
│   ├── filesystem/                 # caminhos e operações locais atômicas
│   └── logging/                    # logging local sanitizado
└── presentation/qt/                # janela, páginas, workers e slots Qt
packaging/
├── pyinstaller/manga_to_kindle.spec
├── windows/app.ico
├── windows/version-info.txt
├── inno/manga_to_kindle.iss         # opcional, após gate de licença
├── notices/THIRD-PARTY-NOTICES.md
└── release/README.md
specs/012-windows-distribution/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
tests/
├── unit/
├── integration/
├── packaging/
└── acceptance/
```

As pastas `src/` e `tests/` são arquitetura-alvo a ser estabelecida pelas features anteriores, não implementação criada por F012. F012 acrescenta os materiais em `packaging/` e mantém o composition root e a migração existentes.

**Decisão de estrutura**: Aplicativo Python único com camadas `domain`, `application`, `infrastructure` e `presentation`; distribuição isolada em `packaging/`; artefatos Spec Kit ficam no diretório da feature.

## Artefatos do Planejamento

- [research.md](research.md): referências oficiais, decisões, APIs/CLI verificadas e pendências.
- [data-model.md](data-model.md): manifest, proveniência, notices, backup/upgrade e checklist.
- [contracts/release-manifest.schema.json](contracts/release-manifest.schema.json): contrato legível por máquina dos insumos/composição normalizados.
- [contracts/artifact-attestation.schema.json](contracts/artifact-attestation.schema.json): hash e estado dos gates por artefato.
- [contracts/installer-lifecycle.md](contracts/installer-lifecycle.md): contrato de instalação, upgrade, cancelamento e remoção de dados.
- [quickstart.md](quickstart.md): sequência futura de validação; comandos não são executáveis neste checkout sem a base da aplicação/lock.

## Rastreamento de Requisitos

| Requisito/critério | Decisão do plano | Evidência futura |
|---|---|---|
| RF-001–RF-012, CS-001, CS-002 | Bundle onedir, Windows nativo, versão/ícone/proveniência; installer opcional. | Build limpa e smoke test por par aprovado. |
| RF-013–RF-019, CS-003, CS-004, CS-008 | Dados fora do app; backup/migração pertencem à aplicação; remover dados somente após confirmação. | Checksums antes/depois em VMs descartáveis e falhas injetadas. |
| RF-009–RF-011, RF-020–RF-023, CS-005, CS-006 | SBOM + notices; bloquear dependências sem licença; KCC/browser ausentes. | Revisão de inventário, licença e ausência do bundle. |
| RF-024–RF-030, CS-007, CS-009 | Checklist com evidência, testes em VMs, comparação de inputs/hashes e zero operações de rede/atualização silenciosa no primeiro início. | Matriz de release assinada por execução; rede bloqueada nos smoke tests. |
| RF-030 | Nenhuma rede na primeira abertura; nenhuma atualização automática. | Captura/inspeção de teste sem tráfego de rede inicial. |

## Controle de Complexidade

Não se propõe uma quarta aplicação, serviço remoto, updater, downloader de dependências opcional ou banco de release dentro do produto. Pydantic é usado apenas em fronteiras JSON; SQLAlchemy permanece na infraestrutura. Inno Setup não é requisito do primeiro artefato e não bloqueia o bundle portátil, salvo os gates de build e validação aplicáveis.
