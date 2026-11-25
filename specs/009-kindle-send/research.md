# Pesquisa — F009 Envio

## Decisões

- Fluxo web manual usa URL oficial indicada pela spec e o shell OS abre a pasta; nunca anexar/selecionar/submeter nem automatizar login Amazon.
- Python 3.12 `smtplib` é suficiente para SMTP, sem dependency externa de protocolo. `SMTP_SSL` inicia TLS desde início; `starttls(context=...)` negocia TLS e requer EHLO depois; exigir `ssl.create_default_context`, timeout finito e hostname/certificate check.
- Biblioteca `keyring` atual documenta Windows Credential Locker e `get_password`/`set_password`/`delete_password`; é candidata para adapter. Forçar apenas backend Windows aprovado; não confiar em backend padrão selecionado via plugins nem aceitar backend arquivo/null. Senha não tem fallback. Travar versão/resolver licença no lock F009.
- SMTP não dá prova de ingestão Amazon/device. Resultado positivo de final DATA é “aceito pelo servidor”; timeout nessa fronteira é “desconhecido” e não autoriza retry.
- Servidor de teste é local fake; não usar SMTP público nem Amazon nos testes.

## Referências primárias

- [Python 3.12 smtplib](https://docs.python.org/3.12/library/smtplib.html)
- [Python 3.12 ssl](https://docs.python.org/3.12/library/ssl.html)
- [keyring docs: supported backends/API](https://keyring.readthedocs.io/en/stable/)
- [keyring Windows backend source](https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py)
- [Amazon Send to Kindle](https://www.amazon.com/sendtokindle)
- [Amazon authorized senders](https://digprjsurvey.amazon.com/csad/help/node/GX9XLEVV8G4DB28H?searchNodes=GDRLC59WEFZTBPU7&theme=light)
- [RFC 5321 SMTP](https://www.rfc-editor.org/rfc/rfc5321/)
- [RFC 3207 STARTTLS](https://www.rfc-editor.org/rfc/rfc3207/)

## Pendências

Confirmar versão e Windows backend/packaging de keyring durante resolução real, com sentinel test. Revalidar canais/formatos/limites Amazon no release; web page acceptance não prova SMTP acceptance.
