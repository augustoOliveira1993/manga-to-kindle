# Quickstart de validação — F008 Biblioteca Local

**Estado**: implementação concluída. A Biblioteca lê os registros persistidos de F003–F007; não cria exemplos no perfil e não acessa rede. A validação manual no Windows continua pendente.

## Iniciar e validar

No PowerShell, na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O comando exato para iniciar a aplicação é `uv run --locked --python 3.12 manga-to-kindle`.

Validação automatizada focada da feature:

```powershell
uv run --locked --python 3.12 pytest tests/integration/test_library_schema.py tests/integration/test_library_search.py tests/integration/test_library_availability.py tests/integration/test_library_history.py tests/integration/test_library_restart.py tests/security/test_library_delete_scope.py tests/ui/test_library_view.py tests/ui/test_main_window.py tests/unit/infrastructure/test_library_mapping.py -q
uv run --locked --python 3.12 pytest tests/acceptance/foundation/test_desktop_startup.py tests/integration/test_desktop_startup.py -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Resultado registrado em 26/11/2026: F008 focada **24 passed**; suíte completa `uv run --locked --python 3.12 pytest tests -q`: **230 passed em 60,33s**; inicialização desktop isolada: **2 passed**; Ruff: **All checks passed**; MyPy: **Success, 117 source files**. A busca com 10.000 mangás e 100.000 capítulos passou a asserção automatizada de até 500 ms. EPUB e CBZ continuam sendo exportações locais F007; a F008 não os envia.

## Roteiro manual

Use uma instalação/perfil descartável ou conteúdo de demonstração recém-importado. A consulta `https://fixture.invalid/manga/demo` é explicitamente sintética; não a trate como fonte real nem como evidência de download. Exemplos de imagem seguros ficam em `examples/demo-import/pasta` e `examples/demo-import/demo.cbz`; nenhum deles é importado automaticamente.

1. Inicie o aplicativo e abra **Biblioteca**. Confirme o estado vazio quando nenhum registro tiver sido criado. A ação **Adicionar mangá** deve abrir a consulta; não deve inserir um mangá de demonstração por conta própria.
2. Em **Adicionar mangá**, consulte a fixture offline e confirme que a Biblioteca passa a mostrar os capítulos persistidos com o marcador **EXEMPLO OFFLINE**. Pesquise `coracao` e `CORAÇÃO`; os mesmos itens devem aparecer. Pesquise autor, título de capítulo, número e volume; depois teste uma busca sem resultados.
3. Marque/desmarque um capítulo como favorito e um mangá sem capítulos como favorito. Ative **Favoritos**, combine com estados de disponibilidade e alterne a ordenação. Feche e abra novamente; os favoritos e as preferências devem permanecer.
4. Importe explicitamente `examples/demo-import/pasta` para um destino local novo. A Biblioteca deve classificar as páginas presentes como **Importado localmente**, sem chamá-las de baixadas. Em **Histórico**, confirme a importação. Exporte um capítulo para EPUB ou CBZ pela tela Conversão e confirme a atividade e o estado da exportação na Biblioteca. Se KCC 13.0.4 estiver disponível, também gere MOBI com um perfil suportado (K810 ou KPW34) e confirme o registro do formato e checksum.
5. Selecione um mangá e use **Remover mangá**. Confira contagens e caminhos exatos. Cancele: os registros e bytes devem permanecer. Confirme somente **Remover registros**: os arquivos gerenciados devem continuar no disco e aparecer em **Arquivos sem vínculo**.
6. Na lista de arquivos sem vínculo, escolha um arquivo disponível e gerenciado, confira categoria/tamanho/caminho no diálogo e cancele; ele deve permanecer. Confirme a exclusão individual; somente aquele arquivo deve desaparecer. Arquivos compartilhados, alterados, ausentes ou fora das raízes gerenciadas devem ficar protegidos. Exports externos só podem ser removidos por caminho individual registrado e hash ainda válido.
7. Confirme que a pasta de origem do exemplo continua intacta. Nenhuma tela da Biblioteca deve fazer requisição de rede, iniciar download ou enviar conteúdo.

## Funcionalidades disponíveis para teste

- Busca local sem distinção de caixa/acentos por título, autor, capítulo, número e volume; filtros combináveis de favoritos, disponibilidade, download e exportação; ordenação estável por título, atividade, estado e capítulo.
- Favoritos e filtros salvos localmente, estado vazio/sem resultados, dados simulados identificados, atualização automática após consulta de catálogo, importação e exportação.
- Disponibilidade derivada de páginas e arquivos verificados: baixado, parcial, não baixado, importado localmente, ausente ou alterado. **F005 ainda não tem fonte autorizada habilitada**, então a aplicação não executa downloads reais.
- Histórico local de downloads, importações e exportações; snapshot de identidade mantém importações/exportações consultáveis depois que o mangá é removido.
- Remoção com prévia e confirmação explícita, plano recuperável, opção de manter registros/arquivos, seleção individual de arquivos e proteção de originais externos, arquivos alterados e caminhos compartilhados.
- Migração Alembic `0006_library`, integridade FK por conexão e recuperação de planos interrompidos.

## Critérios que aguardam validação manual

- No Windows 10/11, revisar disposição, contraste, teclado, leitor de tela e tema claro/escuro em Biblioteca, filtros, histórico e diálogos de exclusão.
- Repetir importação, busca e consulta da Biblioteca em perfil descartável; validar reabertura e estado persistido pela interface.
- Conferir remoção cancelada, remoção de registros sem arquivos e exclusão individual com os exemplos descartáveis; verificar que a origem externa continua byte a byte intacta.
- A busca em 110.000 registros passou o limite automatizado de 500 ms no ambiente local. Confirmar responsividade visual em um PC Windows representativo.
- Não há validação de download real pendente da F008; o primeiro download real é um gate próprio da F005 e requer uma fonte autorizada.
