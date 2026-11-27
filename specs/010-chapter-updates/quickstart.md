# Quickstart de Validação — F010

**Estado**: infraestrutura local implementada; consulta a fonte real bloqueada. Este checkout não possui provedor com autorização de consulta de catálogo e limites revisados. A fixture não habilita F010 nem é usada como evidência de integração remota.

## Preparar e executar

No PowerShell, na raiz do projeto:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação.

## Roteiro manual disponível neste checkout

1. Inicie a aplicação e, em **Adicionar mangá**, consulte apenas `https://fixture.invalid/manga/demo`. Confirme o aviso de demonstração e que nenhuma URL externa foi consultada.
2. Abra **Atualizações**. A consulta cria um snapshot de catálogo identificado como demonstração e a tela mostra a linha com “Demonstração; atualização bloqueada”. **Atualizar** e **Monitoramento periódico** ficam desabilitados; avisos de novidade não são inventados. A tela recarrega o estado local ao ser aberta.
3. Abra Downloads e Enviar ao Kindle. A fixture não cria download, exportação ou transferência. A tela de atualização não inicia atividade ao ser aberta.
4. Feche e reabra o aplicativo. Sem uma preferência persistida elegível e provedor autorizado, nenhum timer periódico ou tráfego de rede deve iniciar.
5. A primeira execução não copia catálogos ou capítulos de demonstração ao perfil. A fixture só persiste quando a consulta explícita é escolhida em Adicionar mangá.

Esse roteiro verifica o gate da UI e a separação da fixture. Ele não valida uma atualização remota real.

## Testes automatizados

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_catalog_updates.py tests/unit/application/test_periodic_update_scheduler.py tests/integration/test_update_repository.py tests/integration/test_catalog_update_flow.py tests/integration/test_update_safety.py tests/ui/test_manual_update_view.py -q
uv run --locked --python 3.12 pytest tests/integration/test_desktop_startup.py tests/ui/test_main_window.py -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes usam SQLite temporário, relógio e provedores de contrato isolados sem acesso à Internet. Eles verificam gate de capacidade, limites por provedor, resposta completa, cancelamento, IDs estáveis, baseline sem avisos, persistência/recuperação, avisos locais e ausência de jobs automáticos. Esses doubles validam o comportamento do aplicativo; não provam autorização, disponibilidade ou compatibilidade de uma fonte real. Os resultados mais recentes ficam no [checkpoint de implementação](../implementation-checkpoint.md).

Validação registrada em 2026-11-26: os seis arquivos de testes focados acima passaram (**27 passed em 5,40s**); os testes de startup e navegação passaram (**3 passed em 1,59s**). Após a correção da atualização do estado ao abrir a tela e o rebuild do bundle F012, a suíte completa passou com **350 passed em 114,11s**, Ruff retornou `All checks passed` e MyPy não encontrou problemas em **151 arquivos**. O smoke do bundle real confirmou a revisão `0010_catalog_updates`. Na verificação manual em perfil temporário, a fixture escolhida explicitamente apareceu como demonstração na tela Atualizações, o status local permaneceu após reiniciar o aplicativo e Downloads continuou sem fonte autorizada. Nenhuma consulta de rede foi usada como evidência.

## Critérios de aceitação que exigem validação manual

- Revisar termos oficiais da fonte escolhida, escopo autorizado para consulta de metadados, atribuição, rate limit, `Retry-After`, intervalo mínimo, estabilidade dos IDs e regras para respostas parciais.
- Confirmar que a fixture aparece somente como demonstração; a ação por mangá e o opt-in ficam desabilitados sem abrir conexão. **Atualizar estado** apenas lê o banco local.
- Com uma fonte aprovada, testar que a primeira resposta completa cria a linha de base sem avisos; IDs conhecidos não repetem aviso, alterações de título/ordem preservam o capítulo e um ID novo gera um aviso local com o título correto.
- Interromper, limitar e falhar uma resposta depois de haver um snapshot válido. A última versão completa, arquivos, seleção e estado do usuário devem permanecer intactos.
- Ativar o monitoramento somente após opt-in explícito por mangá, definir intervalo igual ou superior ao mínimo documentado e confirmar que o limite agregado do provedor vale entre mangás.
- Fechar o aplicativo e confirmar que o timer para; reabrir não deve produzir rajada de verificações vencidas. Desativar o opt-in durante uma consulta pode concluir uma resposta já iniciada, mas nenhuma verificação futura deve ser programada.
- Abrir **Ver avisos**, conferir títulos e horários locais e marcar os avisos exibidos como lidos. Confirmar que isso não cria `DownloadJob`, exportação ou `TransferJob`.

## Disponível e ainda não implementado

- Disponível para teste: esquema `0010_catalog_updates`; `source_chapter_id` estável e escopado ao catálogo; reconciliação sem heurística por título/número; histórico e preferências por mangá; baseline; deduplicação; avisos locais persistidos com título; UI de estado, leitura de avisos e controles de opt-in; scheduler somente em processo e condicionado à política da fonte.
- Não implementado neste checkout: adapter de consulta para uma fonte real com autorização revisada. Por isso, atualização remota manual e periódica permanecem desabilitadas no produto. O canal de demonstração `fixture.invalid` não serve de fallback para elas.
- Não existe envio, download ou serviço em segundo plano iniciado por esta feature.

O gate e a validação final da fonte real permanecem registrados no checkpoint. A aplicação continua executável pelo comando acima.
