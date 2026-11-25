# Quickstart de Validação — F002

## Preparação

Requer Windows 10/11, Python 3.12+ e `uv`. Na raiz do repositório:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O lock existente já inclui PySide6. Não atualize dependências para executar este roteiro.

## Verificação manual da interface

1. Confirme que a janela abre e que a barra lateral oferece Biblioteca, Adicionar mangá, Downloads, Conversão e Configurações.
2. Use `Ctrl+1` até `Ctrl+5` para percorrer as páginas; confirme foco visível, ordem de Tab e que o estado/seleção não trava durante a navegação.
3. Em Adicionar mangá, informe `https://example.test/manga` e escolha “Catálogo de demonstração disponível”. Confirme que aparecem cinco capítulos marcados como demonstração e que nenhum endereço é enviado ou consultado na rede.
4. Marque e desmarque capítulos por mouse e por `Espaço`; use “Selecionar nenhum” e confirme o resumo da seleção.
5. Em Downloads, execute as opções de sucesso, lista vazia, falha e cancelamento. Navegue para outra página durante a execução e confirme que a janela continua respondendo.
6. Em Conversão, escolha pasta, capítulos, perfil e formato de demonstração. Inicie e cancele a prévia; confirme que a pasta não recebe arquivos.
7. Alterne tema claro/escuro, encerre pelo fluxo normal, reabra o aplicativo e confirme que o tema foi persistido.
8. Confirme que URL, credenciais e conteúdo não aparecem em mensagens de erro nem nos logs.

Todas as opções apresentadas como demonstração usam fixtures locais. Não há integração de rede, download, autenticação, geração de arquivo ou envio ao Kindle na F002.

## Verificação automatizada

```powershell
uv run --locked --python 3.12 pytest tests/unit tests/integration tests/acceptance/foundation tests/ui -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes Qt configuram `QT_QPA_PLATFORM=offscreen` via `tests/conftest.py`; não substituem abrir e percorrer a janela em Windows real. Em 25/11/2026, a suíte combinada de F001/F002 passou com 50 testes; Ruff e MyPy também passaram. A validação visual manual em Windows 10/11 permanece pendente (`MANUAL_VALIDATION_PENDING`).
