# Plano Técnico Integrado — Manga to Kindle

**Estado do checkout**: especificações F001–F012 presentes; nenhum código do produto, `pyproject.toml` ou `uv.lock` foi encontrado. Este documento harmoniza os planos das features; não substitui suas specs nem a constituição.

## Direção arquitetural

Aplicativo desktop local para Windows 10/11, Python 3.12+, PySide6. Um único pacote `src/manga_to_kindle/`, organizado em quatro camadas. Dependências apontam para dentro; a composição concreta ocorre na inicialização.

```text
src/manga_to_kindle/
├── domain/                 # entidades, value objects, regras e portas
├── application/            # casos de uso, DTOs, políticas e coordenação
├── infrastructure/         # SQLite/SQLAlchemy/Alembic, FS, HTTP, conversores, SMTP
└── presentation/qt/        # janela, páginas, view models, workers e sinais Qt
tests/{unit,integration,ui,acceptance}/
```

Pacotes por camada agrupam as responsabilidades de domínio, catálogo, fila, importação, exportação, biblioteca, envio, atualizações, perfis e release; não se cria uma arquitetura vertical duplicada para cada feature. `domain` não importa PySide6, SQLAlchemy ou clientes externos. `application` depende de portas tipadas; `infrastructure` implementa essas portas; `presentation` invoca casos de uso e traduz resultados em estados PT-BR. Um composition root constrói e injeta dependências.

## Componentes compartilhados e propriedade

| Responsabilidade | Proprietário | Contrato comum / regra |
|---|---|---|
| Configuração, diretórios locais, logging, startup/shutdown e mecanismo/schema inicial | F001 | Caminhos Windows por `QStandardPaths`; SQLite/Alembic e logs rotativos sanitizados. Cada feature persistente entrega sua revisão. |
| Entidades e IDs | F001 | `Manga`, `Chapter`, `Page`, `DownloadJob`, `DeviceProfile`, `Export`; identidade interna estável separada de rótulos/posição. |
| Tela e apresentação | F002 | Interface PT-BR; workers Qt; estado/progresso/cancelamento encaminhados por sinais. |
| Descoberta e validação de URL/provedor | F003 | `MangaProvider`; somente fixtures locais até autorização verificável; validação de cada redirect e destino DNS/IP. |
| Consulta, ordenação e seleção do catálogo | F004 | IDs estáveis; atualização em lote; ordenar número decimal/especial sem substituir identidade por índice. |
| Fila e gravação de páginas remotas | F005 | Uma política global de concorrência (máximo 2) e timeouts/retry; transporte fake até remoção aprovada de B003. |
| Ingestão local e derivados | F006 | `ImageImportJob`; validadores de path/arquivo; Pillow; originais imutáveis e derivados em caminhos separados. |
| Artefatos exportados | F007 | `Export`; gerador local somente após gates de licença/capacidade; KCC opcional via adaptador de processo validado. |
| Persistência e busca da biblioteca | F008 | SQLAlchemy 2/Alembic; sessão curta por unidade de trabalho, nunca compartilhada entre threads; arquivos sob manifesto/checksum. |
| Autorização de transferência | F009 | Confirmação explícita por envio; padrão abre serviço oficial e pasta local; SMTP opcional e credencial em cofre do SO. |
| Agendamento de atualização | F010 | Manual e timer apenas durante o app; off por padrão; sem download/envio automático; consultas submetidas aos limites do provedor. |
| Preferências e snapshot de perfil | F011 | Perfis de fábrica imutáveis; snapshot por job/export; validação centralizada dos valores usados em F005–F007. |
| Empacotamento e ciclo de release | F012 | Build Windows nativo com PyInstaller; dados fora da instalação; manifest/licenças; instalação/update/uninstall preservam dados. |

## Fluxos e contratos entre módulos

1. **Consulta**: F002 submete URL a F004; F004 usa o registro e `MangaProvider` de F003; a resposta é validada e publicada atomicamente na biblioteca F008. Até B003, apenas `fixture.invalid` roteia para dados sintéticos locais; nenhum request real.
2. **Download**: seleção de F004 gera comando para F005, que exige capacidade/autorização F003 e aplica teto do provedor e configuração F011. F005 grava em staging local, valida MIME/assinatura/decodificação e renomeia atomicamente; progresso segue por sinais Qt. Até B003, somente transporte fake.
3. **Importação e processamento**: F006 recebe caminhos escolhidos pela pessoa usuária, valida todo lote/arquivo antes de publicar entidades via F008 e gera derivados separados; F011 fornece snapshot do perfil.
4. **Exportação**: F007 lê páginas/origem imutáveis e snapshot de F011, produz arquivo em staging, valida e move para destino configurado; registra `Export` em F008. Falhas não deixam um export parcialmente marcado como pronto.
5. **Envio**: F009 recebe `Export` finalizado por F007/F008; fluxo padrão abre navegador e pasta após ação manual. SMTP só com configuração de usuário, destinatário autorizado e confirmação individual; “aceito pelo servidor” nunca é “entregue”.
6. **Atualização**: F010 consulta via F003/F004 sob capacidades, rate limit e intervalo efetivo; publica catálogo/avisos em transação. Notificação não instancia `DownloadJob` ou transferência.

## Persistência, migrações e operações atômicas

- SQLite fica na raiz de dados local da aplicação, fora do diretório de instalação. F001 cria engine, runner Alembic e baseline; cada feature que persiste dados (incluindo F005–F007 e F009–F011) acrescenta sua revisão incremental. F008 consolida relacionamentos, integridade e busca sobre entidades existentes; não recria migrations já necessárias. Revisões aplicadas são imutáveis e cada mudança é recuperável.
- ORM só em `infrastructure.persistence`; modelos de domínio não são entidades SQLAlchemy. `Session` é criada por unidade de trabalho/thread e encerrada com commit/rollback explícito. Ativar e testar foreign keys por conexão; restrições únicas para IDs de fonte/capítulo e deduplicação.
- Arquivos duráveis são referenciados por caminho relativo gerenciado, tamanho, checksum, tipo e estado. Gravações multi-etapa usam `.part`/staging sob diretório controlado, validação e `os.replace` no mesmo volume; no startup, reconciliar journal/manifest e remover somente temporários próprios órfãos.
- Backup do banco antes de migração de release; migration failure interrompe o startup com mensagem acionável, restauração e logs sem conteúdo de livro. Falhas de arquivo/banco não promovem estados de sucesso prematuramente.

## Concorrência, erros e observabilidade

- Nenhum disco, rede, ZIP, Pillow, SMTP ou processo KCC no event loop da UI. `QObject` worker movido para `QThread` com sinais de início/progresso/resultado/erro/cancelamento; não subclassar `QThread` para colocar slots de trabalho. Encerramento solicita cancelamento, aguarda checkpoint limitado e persiste estado retomável.
- Camadas de aplicação convertem falhas de infraestrutura em erros tipados (entrada inválida, provedor não suportado, autorização ausente, limite, timeout, arquivo inválido, conflito, falha persistente, cancelamento). A UI mostra texto PT-BR orientado à ação; logs registram ID interno, etapa e classe/código sanitizado.
- Rotação por tamanho com `RotatingFileHandler`; redigir URLs completas, query strings, tokens, cabeçalhos, credenciais, caminhos pessoais e conteúdo de livro. Segredos SMTP não entram em SQLite, configuração ou logs.
- IDs de correlação locais e progresso determinístico por página/capítulo ajudam suporte sem telemetria externa.

## Segurança, dependências e gates transversais

- Validação de URLs HTTP/HTTPS, userinfo recusado, redirect manual limitado a cinco com revalidação de esquema/host/IP em cada salto e garantia contra DNS rebinding/SSRF. Recusar IP privado, loopback, link-local, multicast, reservado ou resposta DNS mista. F003 limita a prova de transporte; não fingir que apenas `httpx` resolve essa política.
- CBZ: validar nomes antes de extrair, sem caminhos absolutos, `..`, links ou destinos fora do staging; aplicar limites cumulativos da F006 e decodificar com limite de pixels.
- Conservar dados e imagens fonte; nenhuma transferência externa sem autorização explícita. Sem contorno de DRM, CAPTCHA, autenticação, paywall ou controle da fonte; limite e licença são específicos a cada capacidade.
- F003 mantém `B003-REAL-SOURCE`; F004/F005/F010 limitam a consulta/execução real e aceitação a fixtures/fakes até aprovação documentada. F006 local e F007 local não herdam esse bloqueio de rede, mas respeitam direitos de conteúdo.
- F007 mantém `B007-EBOOKLIB-LICENSE`, `B007-EBOOKLIB-FXL`, `B007-KCC-NETWORK`, `B007-KCC-CAPABILITY`. F012 mantém `B012-IMPLEMENTATION-BASELINE`, `B012-ARCH-MATRIX` e revisão de licença Inno Setup. Gates bloqueiam apenas adaptador/release dependente.
- Grupos de dependências a serem decididos e travados em `uv.lock` após compatibilidade real: runtime PySide6/SQLAlchemy/Alembic/Pydantic aplicável; Pillow F006; HTTPX/BeautifulSoup somente provedor autorizado; EPUB library após gate; tooling Ruff/MyPy/Pytest; PyInstaller só F012. Sem versão escolhida neste checkout vazio.

## Testes e definição de pronto

- `unit`: domínio puro, ordenação, validação, estados, policies e limites com relógio/transport fake.
- `integration`: SQLite temporário + migrações; filesystem temporário; archive/image fixtures; SMTP local simulado; export validator e adaptador de processo stub; falhas entre staging/commit.
- `ui`: Qt offscreen, navegação por teclado, tema, estados, cancelamento e atualização via sinais; verificar janela responsiva sem sleeps frágeis.
- `acceptance`: cada cenário mensurável da spec, dados fictícios claramente sinalizados, início/encerramento/reinício e regressão de preservação de originais. Teste de fonte real, KCC/EPUB fixed-layout e dispositivo Kindle só após os gates correspondentes; marcar pendente quando não executado.
- Ruff, MyPy e Pytest são obrigatórios conforme constituição; `uv.lock` reproduz versão. Este planejamento não instalou dependências, não executou lint/tipos/testes e não usa rede do produto.

## Dependências de implementação

`F001 → F002 → F003 → F004 → F005 → F006 → F007 → F008`; F006 necessita de identidade/ordem de F004/F005; F008 consolida dados e consultas após F001–F007. F009 depende de F007/F008; F010 depende de F003/F004/F005/F008; F011 depende de F001/F002/F005/F006/F007/F008; F012 fecha o conjunto após F001–F011. Cada recurso persistente é migrado na feature que o introduz usando o mecanismo único F001; F008 não adia nem recria tabelas necessárias. Consulte [planning-status.md](planning-status.md) e planos individuais.
