# Quickstart e roteiro de validação — F007

**Estado**: marco F007 disponível para teste local. Exporta EPUB 3 e CBZ nativamente; MOBI requer que a pessoa usuária selecione a CLI KCC 13.0.4. A versão real foi testada em Windows x64, mas a compatibilidade em Kindle físico/Send to Kindle não foi validada.

## Instalar, iniciar e testar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando inicia a aplicação. Para manter a demonstração separada da biblioteca existente, inicie com uma raiz de QA nova:

```powershell
$qaRoot = Join-Path $env:TEMP ("MangaToKindle-F007-" + [guid]::NewGuid().ToString("N"))
$env:MANGA_TO_KINDLE_DATA_ROOT = $qaRoot
uv run --locked --python 3.12 manga-to-kindle
```

A raiz temporária mantém banco, configuração, logs e imagens fora do perfil real. O aplicativo não carrega nem importa os exemplos sozinho.

Suíte focada F007 e regressões de inicialização/migração:

```powershell
uv run --locked --python 3.12 pytest tests/unit/application/test_export_plan.py tests/unit/application/test_export_partitioning.py tests/unit/infrastructure/test_kcc_adapter.py tests/integration/test_export_staging.py tests/integration/test_native_epub.py tests/integration/test_cbz_export.py tests/integration/test_export_library_flow.py tests/integration/test_export_fallback.py tests/integration/test_kcc_export_real_binary.py tests/integration/test_library_schema.py tests/integration/test_desktop_startup.py tests/security/test_epub_validation.py tests/security/test_export_no_send.py tests/ui/test_conversion_export.py -q
```

O teste `test_kcc_export_real_binary.py` é ignorado sem `M2K_KCC_EXE`. Para executá-lo com a CLI oficial 13.0.4 previamente obtida:

```powershell
$env:M2K_KCC_EXE = "C:\caminho\para\tool_cli_c2e_13.0.4_AMD64.exe"
uv run --locked --python 3.12 pytest tests/integration/test_kcc_export_real_binary.py -q
Remove-Item Env:M2K_KCC_EXE
```

Validações estáticas:

```powershell
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Resultados finais desta implementação: suíte focada F007 **54 passed em 21,05s**; integração com a CLI KCC 13.0.4 real incluída. Regressão completa **363 passed em 133,91s**; F012 packaging **24 passed em 23,16s**; Ruff `All checks passed`; MyPy sem issues em 153 arquivos. Os testes de startup desktop e do bundle instalado confirmaram a migração `0011_mobi_export_artifacts`. A CLI não é necessária para EPUB ou CBZ.

## Ferramentas e evidência do KCC

Baixe manualmente somente a CLI oficial Windows AMD64 pela [release KCC v13.0.4](https://github.com/ciromattia/kcc/releases/tag/v13.0.4), arquivo `tool_cli_c2e_13.0.4_AMD64.exe`. O aplicativo não baixa, instala nem empacota o KCC. O hash observado é `AC245FE431063875CBE5290731094356655ACCCE3217048AE3ECB7E63F210C22`; a assinatura Authenticode da cópia verificada era válida, SignPath Foundation. Confira o arquivo recebido antes de escolhê-lo:

```powershell
Get-FileHash "C:\caminho\para\tool_cli_c2e_13.0.4_AMD64.exe" -Algorithm SHA256
(Get-AuthenticodeSignature "C:\caminho\para\tool_cli_c2e_13.0.4_AMD64.exe").Status
```

O help real capturado e a proveniência (release, hash e assinatura) ficam em [`tests/fixtures/kcc`](../../tests/fixtures/kcc). A integração verifica novamente `--help` ao exportar e só aceita KCC 13.0.4 com as opções necessárias. O executável selecionado é invocado sem shell, em worker, com cópias das páginas processadas dentro do staging; o KCC não recebe os caminhos dos originais. Timeout é 15 minutos; cancelamento encerra o processo e descarta temporários.

O formato MOBI foi executado com sucesso em três páginas sintéticas usando `K810` (600×800) e `KPW34` (1072×1448). Outros tamanhos e perfis não estão habilitados para MOBI. Idioma precisa ser explícito para não adotar o idioma padrão do KCC. A divisão por tamanho não foi verificada para MOBI e precisa ficar desativada. Ausência de autor é passada vazia ao KCC, sem usar seu autor padrão. O formato exportado continua `.mobi`; não há alegação de AZW3 puro nem de que o envio Kindle o aceite.

O EPUBCheck 5.4.0 é ferramenta de validação externa de desenvolvimento, não uma dependência de execução. Para verificar um EPUB, quando Java e o JAR estiverem disponíveis:

```powershell
java -jar .\tools\epubcheck-5.4.0\epubcheck.jar "C:\caminho\para\capitulo.epub"
```

A fixture EPUB 3 fixa passou com 0 erros fatais, 0 erros e 0 advertências. A suíte valida recursos locais, sumário, metadados, ordem do spine, direção e conteúdo corrompido.

## Roteiro manual

Os exemplos em [`examples/demo-import`](../../examples/demo-import) são imagens sintéticas estáticas. Execute o app com `MANGA_TO_KINDLE_DATA_ROOT` descartável, conforme acima, e escolha os exemplos explicitamente.

1. Abra **Importar imagens** e selecione `examples/demo-import/pasta` ou `examples/demo-import/demo.cbz`. Revise ordem e prévia; confirme autorização para este material sintético e conclua a importação local.
2. Abra **Conversão**, atualize a lista e marque o capítulo importado. Escolha outra pasta vazia para saída.
3. Gere EPUB com idioma `pt-BR` e, depois, CBZ. Confira quantidade, ordem, sumário, direção e que um arquivo existente não foi substituído. EPUB mantém o botão para o fluxo F009; CBZ não declara direção universal.
4. Selecione **MOBI — KCC CLI 13.0.4** e navegue até o executável oficial verificado. Use o mesmo perfil usado em F006: 600×800 (K810) ou 1072×1448 (KPW34). Preencha idioma, direção e mantenha limite por arquivo em zero.
5. Clique **Criar arquivos locais**. Confirme o `.mobi` na pasta escolhida. Para conferir o cabeçalho, leia os bytes 60–67: a assinatura observada é `BOOKMOBI`. A Biblioteca deve registrar formato, caminho e hash; os originais continuam intactos.
6. Repita sem selecionar KCC e confirme que EPUB/CBZ continuam disponíveis. Para ensaiar erro, escolha uma versão não compatível apenas no ambiente descartável; o app deve recusar antes de iniciar conversão.
7. Cancele uma conversão maior enquanto o KCC estiver trabalhando. Confirme que o app retorna, nenhum MOBI parcial é publicado e os originais/arquivos previamente existentes permanecem intactos.
8. Abra EPUB e MOBI em leitores locais compatíveis e anote o resultado. Isso não comprova compatibilidade Kindle.

## Critérios de aceitação para validação manual

- Windows 10/11: navegação por teclado/leitor de tela, foco, rolagem, rótulos, tema, diálogos, seleção de KCC e responsividade durante a conversão.
- EPUB: leitor local, capa, sumário, ordem e RTL/LTR; CBZ: sequência de páginas e comportamento definido pelo leitor.
- MOBI: conversões nos perfis K810 e KPW34, idioma e ausência de autor; ausência/versão incompatível, timeout, cancelamento, colisão e falha não podem alterar originais nem publicar resultados parciais.
- Kindle físico: ainda pendente. Registrar checksum do arquivo, modelo/geração, firmware, rota USB ou Send to Kindle e resultado de páginas, capa, sumário e direção. Ensaiar fixed layout por Send to Kindle separadamente antes de alegar suporte.

## Disponível para teste

- EPUB 3 fixo e CBZ nativos, sem KCC; agrupamento, validação, divisão suportada, staging, cancelamento e histórico local.
- MOBI criado pela CLI oficial KCC 13.0.4 escolhida explicitamente, com perfis 600×800/K810 ou 1072×1448/KPW34, idioma obrigatório e sem limite de tamanho.
- Migração `0011_mobi_export_artifacts`; exportação integrada à Biblioteca e preservação dos originais.
- Dados de demonstração sintéticos importados somente após seleção explícita em perfil temporário.

## Ainda não implementado ou validado

- Download real F005 e atualização remota F010 aguardam fonte autorizada.
- O aplicativo não envia MOBI ao Kindle; o fluxo F009 atualmente aceita EPUB. Nenhuma transferência externa é automática.
- Compatibilidade física Kindle/Send to Kindle para EPUB e MOBI não foi validada; o layout EPUB não é anunciado como aceito pelo Send to Kindle.
- KCC não é instalado/baixado nem incluído no bundle; somente 13.0.4 e os dois perfis verificados estão liberados.

Os critérios e resultados estão em [`specs/implementation-checkpoint.md`](../implementation-checkpoint.md).
