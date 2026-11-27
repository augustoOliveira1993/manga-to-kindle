# Quickstart e validação — F009

## Preparar e iniciar

Requisitos: Windows 10/11, Python 3.12 e `uv`. Na raiz do checkout:

```powershell
uv sync --locked --python 3.12
uv run --locked --python 3.12 manga-to-kindle
```

O segundo comando inicia a aplicação. A revisão `0007_transfers` é aplicada pelo runner central do F001; preferências, perfil sem segredo e histórico ficam no perfil local do usuário. O segredo SMTP é guardado exclusivamente no Gerenciador de Credenciais do Windows.

## Funcionalidades disponíveis para teste

- Ação manual após exportar EPUB: abre a pasta local e a página oficial do Send to Kindle somente após clique; a seleção e o envio no site continuam manuais.
- Seleção de um EPUB exportado, verificação de caminho, tamanho e SHA-256 antes de abrir ou preparar envio.
- Cadastro opcional de host, porta, STARTTLS ou TLS implícito, remetente, um destino Kindle, usuário e segredo SMTP. A autorização do remetente e o endereço de destino são autodeclarados e não consultados na Amazon.
- Teste de conexão por ação explícita; estabelece TLS validado e autentica quando configurado, sem enviar envelope ou conteúdo.
- Prévia por tentativa com arquivo, tamanho, checksum abreviado, destino, remetente e servidor; confirmação independente do destino e remetente, além de nova confirmação para possível duplicata.
- Envio de um único EPUB por mensagem, resultado SMTP, histórico local com destino mascarado, rejeição temporária/permanente e estado desconhecido após desconexão ambígua. Não há repetição automática.
- TLS valida certificado e identidade do host. O modo configurado é obrigatório; erro de certificado ou falta de STARTTLS bloqueia o envio. Mensagens SMTP têm limite local de 50.000.000 bytes, incluindo MIME/base64 estimado e medido.

Para gerar uma demonstração sem tocar em dados existentes, importe explicitamente `examples/demo-import/pasta` para um destino temporário, processe as páginas e exporte um EPUB em outra pasta temporária. Os arquivos são imagens sintéticas e não são copiados ao perfil nem importados automaticamente. Um transporte SMTP de teste usado pelos testes automatizados só aceita loopback e nunca é habilitado no perfil real da aplicação.

## Testes automatizados da feature

```powershell
uv run --locked --python 3.12 pytest tests/unit/domain/test_transfers.py tests/unit/application/test_manual_transfer.py tests/security/test_credential_vault.py tests/security/test_transfer_no_automation.py tests/integration/test_transfer_repository.py tests/integration/test_smtp_send.py tests/unit/application/test_smtp_settings.py tests/unit/application/test_smtp_send.py tests/unit/infrastructure/test_smtp_transport.py tests/ui/test_smtp_settings_view.py tests/ui/test_transfer_result.py tests/ui/test_conversion_export.py tests/ui/test_main_window.py -q
uv run --locked --python 3.12 ruff check src/manga_to_kindle tests
uv run --locked --python 3.12 mypy src/manga_to_kindle
```

Os cenários de envio usam uma conexão TLS real para um servidor SMTP temporário em `127.0.0.1`, certificado local de teste e EPUB gerado pelo pipeline real F006→F007. Cobrem anexo sem alteração, autenticação, STARTTLS, TLS implícito, certificado inválido, teste sem envelope, respostas 4xx/5xx, timeout e desconexão após DATA. Nenhuma conexão automatizada acessa Internet, Amazon, conta real ou Kindle. O teste de Gerenciador de Credenciais usa uma API em memória; um round-trip temporário também foi executado no cofre do Windows e a credencial foi removida.

## Roteiro de teste manual

1. Inicie pelo comando acima e confira que a janela abre sem preencher biblioteca, importar exemplos ou iniciar conexão de rede.
2. Importe `examples/demo-import/pasta` para uma pasta de dados descartável, processe as imagens e exporte um EPUB em um diretório temporário.
3. Em **Enviar ao Kindle**, escolha o EPUB e acione **Abrir no Send to Kindle**. Verifique que o Explorer abre a pasta correta e o navegador abre `https://www.amazon.com/sendtokindle`. O app não seleciona arquivo, inicia sessão ou envia conteúdo.
4. No Windows, confira configuração do perfil com um SMTP de teste que você controla e que ofereça TLS válido. Marque as duas autodeclarações; confira que salvar o perfil não abre conexão. A senha digitada deve ser limpa do campo após salvar e mantida no Gerenciador de Credenciais.
5. Use **Testar conexão**. Confira no servidor de teste que houve somente TLS e, se aplicável, autenticação; nenhum `MAIL`, `RCPT`, `DATA` ou arquivo deve ser submetido.
6. Se for validar o envio na UI, use apenas um destino descartável/controlado e o EPUB sintético. Confira arquivo, checksum, remetente, destino e host na confirmação; cancelar deve produzir zero tentativa de rede. Confirme conscientemente o envio e observe o histórico. Se o servidor aceitar, a mensagem deve dizer **Aceito pelo servidor SMTP — entrega ao Kindle não confirmada**.
7. Altere ou remova o EPUB depois da exportação e tente preparar o fluxo novamente. A divergência de checksum deve bloquear a ação. Reinicie a aplicação e confira o histórico, destino mascarado e ausência de reenvio automático.
8. No Windows 10/11, revise navegação por teclado, foco, contraste, rótulos acessíveis, mensagem de falha separada de pasta/navegador e comportamento quando o cofre está indisponível.

## Critérios de aceitação para validação manual

- Conferir no Windows 10/11 que os atalhos de sistema abrem apenas após ação explícita e indicam claramente falha individual de abertura.
- Conferir fluxo por teclado e leitor de tela nos campos SMTP, caixas de autorização, botão de teste, diálogo por tentativa e histórico.
- Confirmar no Gerenciador de Credenciais que a senha não aparece na configuração, SQLite, histórico, interface após salvar ou log; remover o perfil deve remover a referência correspondente.
- Confirmar que o teste de conexão não submete e-mail e que nenhuma operação inicia antes da confirmação individual.
- Confirmar que um aceite SMTP nunca aparece como confirmação de entrega, e que histórico reiniciado preserva horário, arquivo e estado com endereço Kindle mascarado.
- Nenhum teste manual de release deve usar conta Amazon, dispositivo Kindle ou servidor SMTP público sem autorização própria. A aceitação da aplicação não certifica a entrega Kindle.

## Ainda não implementado ou não verificado

- A aplicação não consulta a Amazon para confirmar o endereço Kindle ou a autorização do remetente; ambos são autodeclarações.
- Não há recibo de entrega, leitura de bounce, ingestão nem confirmação no Kindle. Compatibilidade física do EPUB continua pendente da validação do F007.
- Não há login/upload web automatizado, API Amazon presumida, envio em lote ou suporte SMTP para CBZ/AZW3.
- Nenhum SMTP público, conta Amazon ou aparelho Kindle foi contatado durante a implementação. A validação manual Windows permanece registrada como pendente e não bloqueia o avanço para as próximas features.
