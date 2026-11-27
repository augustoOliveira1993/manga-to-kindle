# Quickstart de Validação — F003

## Estado e fontes disponíveis

- **NDL Next Digital Library** — consulta pontual de metadados de um item individual do
  acervo Public Domain Mark e referências IIIF para suas páginas. Informe uma URL como
  `https://lab.ndl.go.jp/dl/book/851650`. O app verifica metadados via HTTPS fixado ao IP
  validado, mantém TLS para o host original e aplica intervalo local de 60 s entre consultas
  de metadados. Páginas usam limite local de até 12 requests IIIF por minuto. Esses limites
  são do aplicativo, não cotas declaradas pela NDL. O endpoint oficial pode redirecionar
  para o host exato `dss-r4-prod-contents-download.s3.amazonaws.com`; cada salto é
  revalidado com HTTPS, host allowlisted, DNS/IP público e TLS. Outros destinos são recusados.
  A atualização periódica não está habilitada.
- **Demonstração offline** — `https://fixture.invalid/manga/demo`, dados fictícios e sem
  qualquer acesso à rede.
- **Outros catálogos de mangá** — ainda não integrados. A NDL não é um catálogo completo de
  capítulos modernos; não consulte conteúdo fora do escopo PDM aprovado.

F003 fornece catálogo e referências IIIF; o primeiro download real local pela fila está
disponível no marco F005. A confirmação é explícita e nenhum item é enviado ou redistribuído.

## Instalar e iniciar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação.

## Roteiro de teste manual

1. Abra **Adicionar mangá** e confirme a lista de fontes: NDL individual PDM, fixture offline
   e indicação de que outros catálogos ainda não estão integrados.
2. Informe `https://fixture.invalid/manga/demo`. Confirme o título **A Biblioteca das
   Estrelas**, sete capítulos fictícios, indicação de demonstração e ordem `1, 1, 1.5, 2,
   10`, seguida dos dois bônus.
3. Consulte a mesma fixture de novo. Confirme IDs e ordem estáveis e que não houve resolução
   DNS nem request de rede. Não apague banco ou dados reais para limpar a fixture.
4. Para validar a fonte real, informe `https://lab.ndl.go.jp/dl/book/851650` e consulte.
   Confirme **北斎漫画**, autoria **葛飾北斎**, volume **５編** e o aviso de item NDL
   **Public Domain Mark**. Esta ação faz uma consulta externa real; não a repita antes de
   transcorrer um minuto. O catálogo não inicia refresh periódico.
5. Informe um endereço NDL malformado, outro host ou `https://example.test/manga` e confirme
   que a aplicação não preenche a tela com dados da fixture nem registra uma fonte externa
   não suportada. `ftp://example.test/manga` deve ser recusado como esquema inválido.
6. Volte à Biblioteca e confirme que o snapshot NDL e a fixture têm proveniência distinta.
   A fixture não deve criar arquivos em Downloads. O item NDL só gera arquivos após seleção
   e confirmação no fluxo F005.

## Critérios de aceitação para validação manual

- No Windows 10/11 x64, conferir mensagens em português, aviso PDM, lista de fontes, foco,
  navegação por teclado e responsividade durante a consulta NDL.
- Confirmar que iniciar, reiniciar ou abrir a fixture não faz DNS/rede. A consulta NDL só
  ocorre após clicar **Consultar catálogo**.
- Confirmar que o texto identifica outras fontes como não integradas e não sugere que a NDL
  cubra capítulos modernos.
- A inclusão NDL no corpus PDM vem dos termos da coleção, pois o endpoint de detalhe não
  retorna campo de direitos por item. Mudança de termos/status precisa de revisão antes de
  ampliar o escopo.

Esses critérios visuais ficam registrados no [checkpoint de implementação](../implementation-checkpoint.md)
e não bloqueiam as próximas features.

## Validação automatizada

Testes isolados e de integração F003:

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_manga_provider.py tests/unit/application/test_provider_registry.py tests/unit/security/test_external_url_policy.py tests/unit/infrastructure/test_pinned_http_transport.py tests/unit/infrastructure/providers/test_fixture_provider.py tests/unit/infrastructure/providers/test_ndl_provider.py tests/security/test_provider_url_policy.py tests/security/test_provider_log_redaction.py tests/integration/test_provider_authorization_gate.py tests/integration/test_provider_catalog_boundary.py tests/integration/test_ndl_catalog_flow.py tests/ui/test_add_manga_view.py -q
uv run --locked --python 3.12 pytest tests/acceptance/foundation/test_desktop_startup.py tests/integration/test_desktop_startup.py -q
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes automatizados usam DNS/transporte injetáveis e não acessam serviços externos.
Separadamente, a consulta autorizada ao PID `851650` retornou 33 páginas. A validação real
F005 baixou as 33 páginas por HTTPS fixado, validou e gravou 108.693.160 bytes no perfil
temporário `C:\Users\augusto.oliveira\AppData\Local\Temp\manga-to-kindle-f005-ndl-qa-pnltd0e1`.
Não foram alterados arquivos do perfil real. Consulte o [quickstart F005](../005-download-queue/quickstart.md)
para repetir o fluxo com um perfil de QA descartável.
