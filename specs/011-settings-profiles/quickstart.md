# Quickstart de Validação — F011

**Estado**: implementada e integrada à F006/F007; validação visual manual pendente. Os testes não acessam rede nem dispositivo Kindle.

## Preparar e executar

No PowerShell, na raiz do projeto:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando é o comando exato para iniciar a aplicação.

## Roteiro manual

Os exemplos em [`examples/demo-import`](../../examples/demo-import) são imagens geométricas sintéticas. Eles só entram na biblioteca se forem escolhidos e importados explicitamente. Para manter a validação isolada, use um perfil local descartável do Windows ou uma coleção e pastas de saída temporárias.

1. Abra **Configurações → Perfil de dispositivo**. Confirme que aparecem Kindle Básico 8ª/10ª geração em 600×800, 167 ppi e Paperwhite 10ª geração em 1072×1448, 300 ppi. O padrão inicial deve ser Básico 10ª, RTL, escala de cinza, margens zero, recorte desligado e qualidade 90.
2. Selecione o Paperwhite e clique **Aplicar perfil e salvar configurações**. Feche e reinicie o aplicativo; confirme que o perfil, dimensões e preferências de pasta continuam selecionados.
3. Tente editar/remover um perfil interno e confirme que os controles ficam protegidos. Duplique um, altere nome, resolução, direção, margens, recorte e qualidade, salve e reabra a aplicação para conferir persistência. A qualidade é informativa enquanto as saídas disponíveis forem PNG sem perda; saída colorida não é oferecida nesta versão.
4. Em **Importar imagens**, escolha `examples/demo-import/pasta`, confirme a autorização da origem local e confira a prévia em 1072×1448. Faça a importação para um mangá/capítulo descartável. Confira no perfil local que as páginas processadas têm esse tamanho e que os originais não mudaram. Se recorte estiver ativo, revise e confirme a prévia antes de processar.
5. Abra **Conversão**, selecione o capítulo recém-importado, o perfil Paperwhite e uma pasta vazia. Crie EPUB e CBZ locais. Com KCC 13.0.4 selecionado, também teste MOBI no perfil suportado Paperwhite 10ª (1072×1448/KPW34), com idioma explícito e sem divisão por tamanho. Confira que a direção declarada e o snapshot do export correspondem ao perfil selecionado. A exportação não reprocessa arquivos antigos nem prova compatibilidade com Kindle.
6. Em **Pastas e recursos**, escolha diretórios locais existentes e independentes para downloads, exports e cache. Teste concorrência 1 e 2, limite de cache 100 MiB e 20 GiB e retenção de 1 e 365 dias. Tente uma pasta inexistente ou sobreposta; a preferência anterior deve permanecer. Alterar o caminho não move arquivos existentes.
7. Clique **Revisar e limpar cache**. A instalação atual não registra prévias/miniaturas de produção, portanto o esperado é nenhum item elegível. A limpeza nunca deve apagar arquivos desconhecidos, originais, derivados, downloads ou exports; o manifesto só aceita categorias `preview` e `thumbnail` e valida checksum antes da remoção.
8. Altere concorrência, perfil e tema. Abra **Restaurar padrões**, cancele e confira que nada mudou; confirme e confira Básico 10ª, concorrência 2, diretórios padrão, cache 1 GiB/30 dias e tema claro. Biblioteca, exports, perfis personalizados, credenciais e logs devem permanecer.
9. Repita a navegação por teclado nos temas claro e escuro. Inspecione se o foco, rolagem, mensagens, campos de caminho e caixas de confirmação continuam legíveis em tamanho de janela reduzido.

## Testes automatizados executados

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_settings_validation.py tests/unit/infrastructure/test_settings.py tests/unit/application/test_device_profiles.py tests/integration/test_settings_persistence.py tests/integration/test_reset_preferences.py tests/security/test_resource_settings.py tests/ui/test_settings_view.py tests/integration/test_image_profile_flow.py tests/integration/test_import_images.py tests/integration/test_library_schema.py tests/integration/test_application_startup.py tests/integration/test_desktop_startup.py -q
uv run --locked --python 3.12 pytest tests -vv
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os testes cobrem defaults e limites, perfis internos imutáveis, customização e unicidade, persistência após reinício, migração, Paperwhite F006→F007, rollback que recusa perder páginas fora de 600×800, segurança do manifesto, confirmação/cancelamento do reset e preservação de biblioteca, exports, perfil e referência de credencial. O teste de inicialização compõe os serviços e aplica Paperwhite a F006/F007. Na validação desta feature, a suíte completa passou: **299 passed em 96,16s**; Ruff: **All checks passed**; MyPy: **Success: no issues found in 140 source files**. O comando focado acima está disponível para repetição.

## Critérios de aceitação que precisam de validação manual

- Windows 10/11: navegar pela tela Configurações com teclado/leitor de tela e confirmar tamanhos, foco, rolagem, contraste e mensagens nos dois temas.
- Conferir visualmente os valores dos três perfis internos com as fontes oficiais registradas na spec; confirmar que nenhum recurso físico é apresentado como ajuste de conversão.
- Importar as imagens sintéticas somente por ação explícita; conferir prévia Paperwhite, direção, recorte, preservação byte a byte dos originais e snapshot do perfil usado.
- Exportar em EPUB/CBZ local e verificar as dimensões e direção com um leitor de EPUB/CBZ instalado. Teste físico Kindle/Send to Kindle continua fora da evidência automatizada.
- Selecionar pastas existentes independentes; confirmar que pasta inexistente, sobreposta ou de rede é recusada e que alterar o default não move conteúdo anterior.
- Confirmar que limpeza com manifesto vazio não remove nenhum arquivo e que um registro alterado/desconhecido fica preservado.
- Cancelar e confirmar restauração. Em ambos os casos, conferir biblioteca, arquivos, exports, perfis personalizados e referência de credencial.

## Disponível e ainda bloqueado

- Disponível: perfis internos e personalizados, preferências persistentes, aplicação do perfil a novas importações/exports, escolha de pastas, concorrência configurável, política de cache limitada pelo manifesto, tema e reset sem perda de conteúdo.
- Limites: não há produtor de cache regenerável ativo; por isso a tela normalmente não terá itens para limpar. Qualidade não altera PNG e cor não é oferecida.
- Ainda bloqueado no produto: download real F005 e atualizações reais F010 aguardam fonte autorizada; F012 ainda precisa do instalador Windows e suas validações. Nenhuma fixture, transporte de teste ou demonstração serve como prova desses fluxos.

O checkpoint com evidências, comandos e estados de aceitação está em [`specs/implementation-checkpoint.md`](../implementation-checkpoint.md).
