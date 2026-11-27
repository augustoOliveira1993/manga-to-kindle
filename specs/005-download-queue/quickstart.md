# Quickstart de Validação — F005: fila de downloads

## Estado e fontes disponíveis

- **NDL Next Digital Library**: download local de um item individual do corpus Public Domain
  Mark após seleção de capítulo e confirmação explícita. O primeiro fluxo real foi validado
  com o item `851650` (**北斎漫画**, 33 páginas). A aplicação não envia nem redistribui os
  arquivos.
- **Demonstração offline**: `https://fixture.invalid/manga/demo`, claramente identificada;
  não habilita downloads.
- **Outras fontes/catálogos**: não integrados. Manga moderno, conteúdo fora do corpus PDM,
  atualizações periódicas e downloads em lote sem seleção seguem bloqueados.

O transporte fixa conexão nos IPs públicos aprovados, mantém validação TLS, revalida cada
redirect e permite somente o host IIIF NDL e o bucket de entrega exato observado. Cada
imagem passa por limite de tamanho/dimensões, assinatura e decodificação integral antes da
gravação atômica. O aplicativo aplica intervalo local de 60 segundos entre consultas de
metadados e até 12 requests ao endpoint IIIF por minuto; esses valores não são cotas NDL.

## Instalar e iniciar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação.

Para manter o teste manual fora do perfil real, use uma pasta temporária dedicada:

```powershell
$env:MANGA_TO_KINDLE_DATA_ROOT = Join-Path $env:TEMP 'manga-to-kindle-f005-manual-qa'
uv run --locked --python 3.12 manga-to-kindle
Remove-Item Env:MANGA_TO_KINDLE_DATA_ROOT
```

## Roteiro de teste manual

1. Inicie a aplicação e confirme que ela informa que a fundação local está pronta. Abrir ou
   reiniciar o app não deve consultar a NDL nem iniciar downloads automaticamente.
2. Em **Adicionar mangá**, confirme a lista de fontes: NDL individual PDM, fixture offline e
   outros catálogos não integrados. Consulte `https://lab.ndl.go.jp/dl/book/851650`.
3. Confira o título **北斎漫画**, autoria **葛飾北斎**, volume **５編**, a indicação PDM e as
   33 páginas. O endpoint não retorna um campo de direitos por item; a elegibilidade decorre
   de sua inclusão no corpus descrito nos termos oficiais da NDL.
4. Selecione o item e clique **Baixar item selecionado**. Recuse a confirmação e confira que
   nenhum job foi criado. Repita, confirme o download local e observe progresso por página.
5. Ao terminar, confira `33/33`, estado **Concluído** e arquivos JPEG válidos sob
   `data\downloads\pages\` do perfil QA. Não procure arquivos em exports nem em outros
   diretórios.
6. Para testar controle/retomada, use um item de QA novo, pause e retome explicitamente; em
   seguida feche o app durante outro job, reabra e confirme estado **Interrompido**, sem
   tráfego automático. A retomada deve reconstruir referências sem nova consulta de catálogo.
7. Consulte a fixture e selecione capítulos. Confirme que o botão de download não aparece e
   que Downloads não recebe jobs nem conteúdo fictício.
8. No Windows 10/11 x64, valide navegação por teclado, foco, leitor de tela, mensagens e
   responsividade enquanto a consulta e o download acontecem.

As consultas pontuais respeitam pelo menos 60 segundos entre consultas de metadados por
instância do provider. Para um primeiro download com todas as páginas, use um perfil QA
vazio; os arquivos existentes válidos são reutilizados em execuções seguintes.

## Dados reais de QA já disponíveis

O smoke real concluído em 27/11/2026 deixou o item PDM `851650` em um perfil temporário
isolado deste checkout:

```text
C:\Users\augusto.oliveira\AppData\Local\Temp\manga-to-kindle-f005-ndl-qa-pnltd0e1
```

Ele contém 33/33 imagens raster validadas e 108.693.160 bytes; a fila terminou com estado
`succeeded`. Para abrir esse perfil em **Downloads** ou **Biblioteca**:

```powershell
$env:MANGA_TO_KINDLE_DATA_ROOT = 'C:\Users\augusto.oliveira\AppData\Local\Temp\manga-to-kindle-f005-ndl-qa-pnltd0e1'
uv run --locked --python 3.12 manga-to-kindle
Remove-Item Env:MANGA_TO_KINDLE_DATA_ROOT
```

Esse perfil é dado real PDM de QA, não fixture nem seed instalado. O perfil local normal do
usuário não foi alterado.

## Validação automatizada

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_download_job.py tests/unit/application/test_download_retry_policy.py tests/unit/application/test_download_queue.py tests/unit/infrastructure/test_download_transport.py tests/unit/infrastructure/test_pinned_http_transport.py tests/integration/test_download_flow.py tests/integration/test_download_restore_references.py tests/integration/test_download_controls.py tests/integration/test_download_repository.py tests/integration/test_download_recovery.py tests/integration/test_atomic_page_save.py tests/integration/test_download_worker.py tests/security/test_download_file_validation.py tests/security/test_download_boundaries.py tests/ui/test_jobs_views.py tests/ui/test_download_controls_view.py tests/ui/test_add_manga_view.py -q
uv run --locked --python 3.12 pytest tests/acceptance/foundation/test_desktop_startup.py tests/integration/test_desktop_startup.py -q
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests tools
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes automatizados usam SQLite temporário, relógio/transporte isolados e não acessam a
internet. Eles cobrem seleção/confirmação, fila, concorrência, progresso, pause/resume/cancel,
retry, redirects aprovados e recusados, validação raster, gravação atômica e recuperação.
O download real registrado acima foi executado separadamente pelo mesmo provider, transporte,
URL policy e fila da aplicação; fixtures não são evidência do fluxo externo.

## Critérios de aceitação para validação manual

- No Windows 10/11 x64, confirmar mensagens, lista de fontes, foco, teclado, leitura acessível
  e ausência de I/O bloqueante na interface.
- Confirmar que só o item NDL real apresenta a ação de download e que a recusa da confirmação
  não cria job. O app deve armazenar apenas depois do consentimento e nunca enviar conteúdo.
- Conferir progresso, pausa, retomada, cancelamento, recuperação após reinício e reutilização de
  páginas já validadas.
- Confirmar que fixture, startup e retomada não iniciam consultas/downloads silenciosos; a
  retomada de referências não deve requerer nova consulta de metadados.
- Conferir que páginas e metadados permanecem no perfil escolhido e que o estado terminal e
  os arquivos coincidem.

Resultados automatizados, smoke de inicialização e critérios pendentes ficam registrados em
[implementation-checkpoint.md](../implementation-checkpoint.md). A validação manual Windows
continua recomendada; não bloqueia a sequência de implementação.
