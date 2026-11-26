# Quickstart de validação — F006

## Preparar e iniciar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação. A F006 usa Pillow 13.0.0 no lock e testa JPEG, PNG, WEBP e orientação EXIF no ambiente Python 3.12 para Windows.

## Roteiro manual

1. Abra **Importar imagens** e selecione `examples/demo-import/pasta`. Clique em **Verificar e pré-visualizar**.
2. Confira a ordem `01.png`, `02.jpg`, `10.webp`, as dimensões, a contagem de itens ignorados e a prévia 600×800 em escala de cinza. Mova uma página para cima/baixo e confira que a posição confirmada muda.
3. Preencha um novo título de mangá e capítulo usando nomes de teste e marque a confirmação de autorização local. Clique em **Importar para este dispositivo** e aguarde o progresso terminar.
4. Reinicie a aplicação e selecione o capítulo local já importado. Importe novamente a mesma pasta: o resultado deve ser idempotente, sem duplicar páginas. A pasta de origem deve permanecer com os mesmos arquivos e bytes.
5. Repita com `examples/demo-import/demo.cbz` para exercitar o leitor CBZ. O aplicativo não deve extrair os nomes do arquivo para o perfil nem fazer conexões de rede.
6. Com uma cópia de teste das imagens, marque **Pré-visualizar recorte de margens** e compare antes/depois. Recorte começa desativado; revise o conteúdo junto às bordas antes de confirmar.
7. Selecione `examples/demo-import/pagina-dupla` e verifique a imagem panorâmica. Marque a página na lista, habilite **Dividir páginas duplas marcadas** e alterne RTL/LTR. Confira a ordem dos dois derivados na prévia. A divisão só se aplica às páginas marcadas.
8. Cancele uma leitura/importação longa se houver um conjunto grande disponível. A operação deve terminar sem publicar lote parcial; reabra o app para confirmar que a recuperação não apaga dados anteriores.
9. Confira que nenhum conteúdo é enviado: tudo fica no perfil local e a interface exige confirmação explícita antes de processar.

Os arquivos em `examples/demo-import` são ilustrações geométricas sintéticas. Eles não são copiados automaticamente para o perfil. Para exercitar recorte, use uma cópia descartável de uma imagem de teste e preserve os originais.

## Verificação automatizada executada

```powershell
uv run --locked --python 3.12 pytest tests/unit/application/test_image_import_validation.py tests/unit/application/test_image_transform.py tests/unit/application/test_crop_and_spread.py tests/security/test_archive_extraction.py tests/integration/test_import_images.py tests/integration/test_original_image_store.py tests/integration/test_image_profile_flow.py tests/integration/test_image_pipeline_recovery.py tests/integration/test_image_transform_worker.py tests/ui/test_image_import_view.py tests/ui/test_image_preview.py -q
uv run --locked --python 3.12 pytest tests -q
uv run --locked --python 3.12 ruff check src tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

## Critérios de aceitação manual pendentes

- No Windows 10/11, conferir foco, contraste, tamanho de janela e rótulos acessíveis na tela nova.
- Confirmar visualmente a ordem e reordenação, prévia em 600×800, EXIF, transparência, escala de cinza e preservação de proporção.
- Revisar se o recorte não remove conteúdo em margens claras e se a prévia da divisão panorâmica respeita a direção RTL/LTR.
- Conferir cancelamento com um lote grande em disco lento e espaço/permissão insuficientes sem perda de dados prévios.
- Confirmar reimportação idempotente, conflito com lote diferente e ausência de qualquer transferência ou conexão.

CBZ malicioso, colisões no Windows, symlink, limites, cancelamento e recuperação também têm cobertura automatizada em fixtures de segurança e integração.
