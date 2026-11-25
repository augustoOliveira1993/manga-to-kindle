# Quickstart de Validação — F001

**Estado**: F001 implementada e validada no ambiente Windows deste checkout com Python 3.12.10. A validação manual em instalação limpa de Windows 10/11 permanece pendente.

1. Em Windows 10/11 com Python 3.12+, restaurar o ambiente travado: `uv sync --locked --python 3.12`.
2. Executar testes da fundação: `uv run --locked --python 3.12 pytest tests/unit tests/integration tests/acceptance/foundation -q`.
3. Executar qualidade: `uv run --locked --python 3.12 ruff check src/manga_to_kindle tests` e `uv run --locked --python 3.12 mypy src/manga_to_kindle`.
4. Abrir manualmente com `uv run --locked --python 3.12 manga-to-kindle`; confirmar que a janela aparece antes da conclusão do bootstrap local. **Pendente de execução manual neste ambiente.**
5. Confirmar que a raiz retornada por `QStandardPaths.AppLocalDataLocation` fica no perfil local do usuário e contém `config`, `data`, `logs` e `cache`.
6. O teste de recuperação injeta uma falha após uma alteração parcial, verifica restauração do banco e reabre a aplicação preservando os dados.
7. O teste Qt agenda um timer durante o bootstrap e confirma que ele é atendido antes do término. O teste de inicialização intercepta conexões de socket e falha se houver tentativa de rede.
8. Os testes cobrem rotação configurável com até três backups, migração idempotente, recuperação de falha, chaves estrangeiras e encerramento ordenado. Repetir dez ciclos de interface em instalação limpa antes do release (**pendente**).

## Evidências da última execução

- Ambiente: Python 3.12.10, Pytest 9.2.0, Ruff 0.17.6 e MyPy 1.20.2.
- Pytest: **28 passaram** (`uv run --locked --python 3.12 pytest tests/unit tests/integration tests/acceptance/foundation -q`).
- Ruff: **All checks passed** (`uv run --locked --python 3.12 ruff check src/manga_to_kindle tests`).
- MyPy: **Success, no issues found in 32 source files** (`uv run --locked --python 3.12 mypy src/manga_to_kindle`).
- `uv sync --locked --python 3.12` concluiu sem alterar o lockfile.
- Teste automatizado Qt confirmou janela pronta, bootstrap em worker distinto da thread gráfica, timer atendido durante o bootstrap e encerramento assíncrono.
- Teste de recuperação confirmou restauração dos dados após falha injetada e reabertura na revisão atual.
- Pendentes: abertura visual manual do comando de execução, teste em Windows 10/11 limpo e dez ciclos manuais de interface.
