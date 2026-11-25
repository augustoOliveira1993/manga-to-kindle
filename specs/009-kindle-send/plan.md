# Plano de Implementação: F009 — Envio ao Kindle

**Branch**: `009-kindle-send` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e limites

Padrão: ação manual abre pasta do Export e página oficial Send to Kindle, sem selecionar/enviar arquivo, login ou automação web. SMTP é opcional; uma exportação e um destinatário por vez, confirmação explícita por tentativa. Sem API Amazon presumida. “Aceito pelo servidor” não significa “Entregue”.

## Arquitetura

`application.transfer` verifica ExportPackage F007 ainda existente/hash válido, prepara consent summary e apenas após confirmação cria TransferJob. `infrastructure.os_open` abre caminho/URL solicitados; não manipula navegador DOM. `CredentialVault` porta usa Windows Credential Locker por adapter candidato `keyring` com backend Windows verificado; falha/ausência de backend segura bloqueia SMTP, sem texto plano. O secret ID vai na config, senha não. `SmtpTransport` usa biblioteca padrão Python `smtplib` por worker; `SMTP_SSL` para TLS implícito ou `SMTP.starttls(context=...)` + novo EHLO, certificado e hostname validados, timeout finito; sem downgrade nem opção de ignorar TLS. API real exata confirmada no Python 3.12. SMTP test connection é ação explícita e não manda livro.

Antes de transmitir, UI mostra path/name, tamanho, hash curto, destinatário, remetente, host/porta, subject/body final e aviso saída do dispositivo. Autorização do destinatário e remetente é autodeclaração, não checada na Amazon. Validação de limite configurado e MIME/formato conforme canal específico; Send-to-Kindle web limit não transfere para SMTP. Não dividir/converter automaticamente. Byte do artifact permanece idêntico; SMTP message encoding size pode ser estimado bounded.

Estados: awaiting_confirmation → connecting/authenticating → transmitting → accepted_by_smtp/rejected/cancelled_before_submission/unknown. 4xx/5xx separadas; sem retry automático; repetir exige consentimento completo. Desconexão após DATA antes de resposta final fica unknown e nunca retenta sozinha; startup reconciles última etapa persistida.

## Persistência, privacidade e testes

TransferJob snapshot guarda export/hash/channel/consent/status/timestamps e host/from/masked-to; sem senha, corpo/anexo/conteúdo. Logs omitem endereços completos, assunto, nome/path, conteúdo e respostas cruas; secret sentinel test. Worker progress signals; cancellation only where outcome remains truthfully known. F008 repositório/migrations, F001 config, F007 exports.

Testar fake vault e SMTP local para success, 4xx/5xx, TLS failure, bad cert, auth, limits, disconnect-after-data unknown, cancel boundaries, restart no retry, checksum mismatch and manual OS open fake. Zero internet/Amazon/device. Estrutura `domain/transfers`, `application/transfers`, `infrastructure/{smtp,credential_vault,os_open}`, UI page. Trace RF-001–033, RNF-001–007, CS-001–009 via [contracts/transfer.md](contracts/transfer.md)/[data-model.md](data-model.md)/[quickstart.md](quickstart.md).

## Dependencies and gates

F001/F002/F007/F008. `keyring` is a versioned candidate with documented Windows Credential Locker API; implementation must force/check backend, test actual Windows and license. Fallback manual always available. SMTP server setup/authorization remain user-controlled; no human decision needed to finish design, but missing secure vault blocks only SMTP option.
