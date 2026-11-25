# Plano de Implementação: F001 — Fundação

**Branch**: `001-app-foundation` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e resumo

Entregar bootstrap local reproduzível: configuração e diretórios idempotentes, logging rotativo sanitizado, SQLite versionado com migração inicial, contratos de domínio, fronteiras de exceção e encerramento seguro. Instalação de desenvolvimento por `uv`; sem rede, downloads ou envio.

## Contexto técnico e constituição

Python 3.12+ / PySide6 / Windows 10 e 11. SQLAlchemy 2 tipado e Alembic são a estratégia compartilhada com F008; Ruff, MyPy e Pytest formam as ferramentas de qualidade. Versões exatas ficam para o primeiro `pyproject.toml` e `uv.lock` validados; nenhum código ou dependência está instalado neste checkout. SQLite fica sob `QStandardPaths.AppLocalDataLocation/data`; configuração, logs e cache em subpastas irmãs. Janela principal disponível em até 10 s no perfil de referência da spec.

Conforme I–V: composição injeta dependências; domínio não depende de Qt/ORM; migrações ocorrem fora do event loop; logs omitem URL/token/segredo/conteúdo; gravações têm backup/staging; zero chamadas de rede. Os limites de tempo e rotação vêm da spec, sem novas metas.

## Arquitetura e componentes

`domain` recebe tipos imutáveis e invariantes; `application.bootstrap` coordena `ensure_directories`, carregar/validar configuração, configurar logging, abrir banco, aplicar migrações e construir shell. `infrastructure.filesystem.paths`, `.config`, `.logging`, `.persistence` implementam portas; `presentation.qt` cria a janela após os pré-requisitos. Bootstrap de disco ocorre antes da janela ou em worker inicial; qualquer I/O potencialmente demorado posterior também usa worker. A composição injeta paths, logger, session factory; testes usam filesystem/DB temporários e transporte de rede proibido.

### Persistência e falhas

SQLAlchemy 2 DeclarativeBase/Mapped e Alembic. Migração inicial cria baseline para Manga, Chapter, Page, DownloadJob, DeviceProfile e Export, sem supor provedor/download real. `Page.original_path` não é gravável pelo conversor. Foreign keys ligadas por conexão; Session por unidade de trabalho/thread, commit/rollback explícito. Migração usa transação quando possível, cópia recuperável antes de DDL não transacional, interrompe startup em falha e mostra recuperação PT-BR.

Config inválida não se substitui silenciosamente: preservar arquivo e oferecer fluxo de correção. Rotação: 5 MiB/arquivo, 3 backups por padrão; filtro de redação aplicado a contexto e traceback. No fechamento: parar novos comandos, solicitar cancelamento, checkpoint e commit/rollback local, fechar DB e handlers. Falha essencial aborta composição sem UI parcialmente inicializada.

## Estrutura planejada

```text
src/manga_to_kindle/{domain,application,infrastructure/{filesystem,config,logging,persistence},presentation/qt}/
  domain/{manga,chapter,page,download_job,device_profile,export}.py
  application/bootstrap/{startup,shutdown}.py
  infrastructure/{paths,config,logging,persistence}/
  presentation/qt/{app,main_window,workers}/
migrations/versions/0001_initial_schema.py
tests/{unit,integration,acceptance}/foundation/
```

## Testes, riscos e recuperação

Testes unitários dos seis contratos, estados terminais e progresso; integração de diretórios idempotentes, config, migration up/re-run/failure, backup, FK e rotação; bootstrap/close com exceções e worker fake; guard que falha em tentativa de socket/rede. Aceitação mede startup ≤10 s, 10 ciclos de abrir/fechar sem perda e rotação configurada. SQLite DDL pode não permitir rollback integral: usar Alembic batch mode, backup verificado e falha injetada. Shutdown não deve abandonar estado incompleto. Suite não executada nesta etapa.

## Rastreabilidade e gates

RF-001/RNF-001: `uv`/lock; RF-002–006/RF-009: paths, SQLite, migrações e ciclo de vida; RF-007–008: logs/exceções; RF-010: [data-model.md](data-model.md) e [contracts/domain.md](contracts/domain.md); RF-011: zero rede; RF-012: README/[quickstart.md](quickstart.md); RF-013/CS-001–007: testes e mensurações acima. F001 não implementa features posteriores. Sem bloqueio humano; versões dependem da resolução posterior.
