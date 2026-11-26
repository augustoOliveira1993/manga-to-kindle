# Quickstart de Validação — F005: fila de downloads

## Estado

A fila persistente, os controles, o retry, a validação raster e a recuperação local estão implementados. Os testes usam transporte isolado. **O marco do primeiro download real continua pendente**: `fixture.invalid` não autoriza download e nenhuma fonte de produção foi aprovada. A interface não cria trabalho a partir da fixture nem inicia tráfego externo.

Não é necessário aguardar a validação manual para continuar as features desbloqueadas. Os itens manuais pendentes ficam registrados abaixo.

## Instalar e iniciar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação depois da instalação.

## Roteiro de teste manual

1. Inicie a aplicação e confirme que o status informa que a fundação local está pronta.
2. Abra **Downloads**. Confirme a mensagem de que não existe fonte autorizada, que o botão de início está desativado e que não há controles de simulação de sucesso/falha.
3. Abra **Adicionar mangá** e consulte `https://fixture.invalid/manga/demo`. Selecione um ou mais capítulos e volte a **Downloads**. A fila deve continuar vazia: a fixture fornece metadados, não permissão de download.
4. Feche e reabra a aplicação. Confirme que a inicialização termina normalmente e que nenhum trabalho ou tráfego começa automaticamente.
5. Navegue pela tela com Tab e teclado. Confira nomes acessíveis, foco visível e a leitura do estado vazio. Com uma fonte autorizada no futuro, os critérios dos controles e do progresso por capítulo/página precisarão ser repetidos nessa tela.

Nenhum dado de demonstração de download é instalado no perfil do usuário. As imagens PNG válidas e inválidas em `tests/fixtures/downloads/` são fixtures automatizadas e não são mostradas como conteúdo real.

## Validação automatizada focada

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_download_job.py tests/unit/application/test_download_retry_policy.py tests/unit/application/test_download_queue.py tests/unit/infrastructure/test_download_transport.py tests/integration/test_database_lifecycle.py tests/integration/test_download_flow.py tests/integration/test_download_controls.py tests/integration/test_download_repository.py tests/integration/test_download_recovery.py tests/integration/test_atomic_page_save.py tests/integration/test_download_worker.py tests/security/test_download_file_validation.py tests/security/test_download_boundaries.py tests/ui/test_jobs_views.py tests/ui/test_download_controls_view.py -q
uv run --locked --python 3.12 pytest tests/acceptance/foundation/test_desktop_startup.py tests/integration/test_desktop_startup.py -q
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes usam SQLite temporário, transporte falso e relógio fixo nas políticas. Eles cobrem concorrência até duas páginas, ordem estável, deduplicação, pausas e cancelamento, retry/`Retry-After`, redirects recusados, associação do endereço conectado, Content-Type, assinatura, tamanho/pixels, staging atômico, recuperação após rename e a barreira sem autorização. Nenhum teste abre conexão externa.

## Critérios que aguardam validação manual

- Conferir no Windows 10/11 a apresentação do bloqueio, o foco, a navegação e os rótulos acessíveis.
- Conferir que consultar a fixture e selecionar capítulos não cria trabalho, não armazena imagem e não acessa rede.
- Validar o fluxo de download em tela, o progresso por capítulo/página e os controles com uma fonte somente depois que existir evidência oficial compatível de autorização local, escopo, hosts, limites, atribuição e remoção. Até lá, esse critério é impeditivo para o marco **F005 — primeiro download funcional**, e não há roteiro de teste real a executar.

As features anteriores continuam no conjunto completo de testes do projeto. O resultado do conjunto e a verificação de inicialização do desktop são registrados em [implementation-checkpoint.md](../implementation-checkpoint.md).
