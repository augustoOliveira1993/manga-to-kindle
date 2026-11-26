# Quickstart e roteiro de validação — F007

**Estado**: MVP local com geração EPUB/CBZ disponível para teste. Nenhum arquivo é enviado ao Kindle ou à rede. KCC não está configurado; compatibilidade com Kindle físico/Send to Kindle ainda não foi validada.

## Iniciar e executar as verificações

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando inicia a aplicação. A suíte F007 focada pode ser executada assim:

```powershell
uv run --locked --python 3.12 pytest tests/unit/application/test_export_plan.py tests/unit/application/test_export_partitioning.py tests/integration/test_export_staging.py tests/integration/test_native_epub.py tests/integration/test_cbz_export.py tests/integration/test_export_library_flow.py tests/integration/test_export_fallback.py tests/security/test_epub_validation.py tests/security/test_export_no_send.py tests/ui/test_conversion_export.py tests/ui/test_jobs_views.py tests/ui/test_main_window.py -q
```

As validações estáticas do repositório são:

```powershell
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Resultados desta implementação: testes focados F007 `41 passed`; regressão completa `205 passed`; inicialização desktop isolada `2 passed`; Ruff e MyPy sem erros. O histórico detalhado está no [checkpoint](../implementation-checkpoint.md).

O EPUBCheck 5.4.0 é uma ferramenta de validação externa de desenvolvimento, não uma dependência de execução. Para verificar um arquivo gerado quando Java e o JAR estiverem disponíveis:

```powershell
java -jar .\tools\epubcheck-5.4.0\epubcheck.jar "C:\caminho\para\capitulo.epub"
```

Resultado registrado nesta implementação: EPUBCheck 5.4.0 terminou com **0 erros fatais, 0 erros e 0 advertências** em uma fixture EPUB 3 fixa. A suíte automatizada do projeto também valida recursos, sumário, metadados, ordem do spine, direção, conteúdo corrompido e referências externas.

## Roteiro manual

Os exemplos em [`examples/demo-import`](../../examples/demo-import) são imagens sintéticas estáticas. O aplicativo nunca os importa automaticamente. Para não misturar esse ensaio a uma biblioteca pessoal, use um perfil de usuário temporário do Windows ou confira os dados do perfil antes de importar.

1. Inicie a aplicação e abra **Importar imagens**.
2. Selecione `examples/demo-import/pasta` ou `examples/demo-import/demo.cbz`; confira a ordem e a prévia 600×800.
3. Confirme que tem autorização para importar a origem local, escolha criar um mangá/capítulo local de demonstração e conclua a importação.
4. Abra **Conversão**, aguarde a lista de capítulos prontos e marque o capítulo importado.
5. Escolha uma pasta local vazia. Selecione `600 × 800 — páginas processadas em F006`, formato EPUB 3 e idioma `pt-BR`. Para teste CBZ, escolha esse formato; o campo de idioma e a direção EPUB deixam de ser aplicáveis.
6. Mantenha o agrupamento por capítulo ou escolha volume quando todos os capítulos tiverem volume explícito. Para testar divisão, informe um limite acima do tamanho de uma página e abaixo do pacote completo.
7. Clique **Criar arquivos locais**. Confirme nomes, quantidade, sumário, direção RTL/LTR, bytes e seções dos arquivos. Se houver conflito de nome, a exportação deve parar sem substituir o arquivo anterior.
8. Cancele uma exportação de várias páginas enquanto ela estiver em andamento; confirme que originais e arquivos anteriores continuam intactos e que nenhum arquivo parcial é publicado.
9. Abra o EPUB em um leitor compatível e registre as observações de layout. Ainda não considere esse ensaio uma validação Kindle.

## Critérios de aceitação que aguardam validação manual

- Interface no Windows 10/11: foco, acessibilidade, rolagem, rótulos em português, tema claro/escuro, EPUB e CBZ.
- EPUB em leitor local: capa gerada quando não há capa local, sumário, ordem e navegação RTL/LTR.
- CBZ: sequência dos nomes de imagem; a direção de leitura é determinada pelo leitor CBZ.
- Exportação por capítulo e por volume, divisão em fronteiras de capítulo/página, cancelamento e colisão de nome sem sobrescrita.
- Abrir o EPUB em um Kindle físico e registrar checksum, modelo/geração, firmware, rota USB ou Send to Kindle e resultado de capa, sumário, direção e páginas. Essa validação ainda está pendente; não há promessa de compatibilidade fixed-layout/Send to Kindle.

## Disponível para teste

- Planejamento por capítulos/volumes com ordem canônica, metadados reais disponíveis e idioma explícito para EPUB.
- Writer EPUB 3 fixo em Python padrão, capa SVG neutra gerada quando ausente, navegação por capítulo, RTL/LTR, validação estrutural e publicação local atômica.
- Writer CBZ com páginas processadas e ordem preservada; divisão por tamanho configurado e cancelamento.
- Histórico local de estado, checksum e caminho dos artefatos no SQLite.

## Ainda não implementado ou validado

- F005 continua sem fonte autorizada para download real.
- Adaptador KCC, detecção de versão/capacidades e formatos KCC não estão disponíveis. O aplicativo não baixa nem inicia KCC.
- Envio/transferência ao Kindle pertence à F009 e não é feito por esta tela.
- Teste físico de compatibilidade Kindle/Send to Kindle permanece pendente.
- A Biblioteca consolidada e o histórico de exportações visível nela pertencem à F008; F007 já persiste os artefatos.

O estado, os comandos executados e os resultados estão em [`specs/implementation-checkpoint.md`](../implementation-checkpoint.md).
