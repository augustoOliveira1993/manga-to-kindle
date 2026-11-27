# Plano de Implementação: F009 — Envio ao Kindle

**Branch**: `009-kindle-send` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e limites

Padrão: ação manual abre pasta do Export e página oficial Send to Kindle, sem selecionar/enviar arquivo, login ou automação web. SMTP é opcional; uma exportação e um destinatário por vez, confirmação explícita por tentativa. Sem API Amazon presumida. “Aceito pelo servidor” não significa “Entregue”.

## Arquitetura

`application.transfers` verifica o artefato F007 e SHA-256, prepara a confirmação e só então cria TransferJob. `infrastructure.os_open` abre pasta/URL solicitadas sem manipular o navegador. A porta `CredentialVault` usa diretamente a API Win32 Credential Manager (`CredWriteW`/`CredReadW`/`CredDeleteW`) sem dependência adicional; o round-trip foi executado no Windows e o segredo removido. Falha/ausência do cofre bloqueia SMTP, sem texto plano. `SmtpTransport` usa Python 3.12 `smtplib` em worker; `SMTP_SSL` para TLS implícito ou `SMTP.starttls(context=...)` seguido de EHLO, certificado e hostname validados e timeout finito; sem downgrade nem opção de ignorar TLS. Testar conexão é ação explícita e não submete mensagem.

Antes de transmitir, UI mostra path/name, tamanho, hash curto, destinatário, remetente, host/porta, subject/body final e aviso saída do dispositivo. Autorização do destinatário e remetente é autodeclaração, não checada na Amazon. Validação de limite configurado e MIME/formato conforme canal específico; Send-to-Kindle web limit não transfere para SMTP. Não dividir/converter automaticamente. Byte do artifact permanece idêntico; SMTP message encoding size pode ser estimado bounded.

Estados: awaiting_confirmation → connecting/authenticating → transmitting → accepted_by_smtp/rejected/cancelled_before_submission/unknown. 4xx/5xx separadas; sem retry automático; repetir exige consentimento completo. Desconexão após DATA antes de resposta final fica unknown e nunca retenta sozinha; startup reconciles última etapa persistida.

## Persistência, privacidade e testes

TransferJob snapshot guarda export/hash/channel/consent/status/timestamps e host/from/masked-to; sem senha, corpo/anexo/conteúdo. Logs omitem endereços completos, assunto, nome/path, conteúdo e respostas cruas; secret sentinel test. Worker progress signals; cancellation only where outcome remains truthfully known. F008 repositório/migrations, F001 config, F007 exports.

Testar cofre e SMTP TLS local para aceite, respostas 4xx/5xx, falha TLS, certificado inválido, autenticação, tamanho, timeout, checksum, desconexão após DATA e restart sem retry. Testar abertura manual sem rede. Nenhum teste automatizado acessa Internet, Amazon ou dispositivo. Estrutura em `domain/transfers`, `application/transfers`, `infrastructure/{transfers,security,os_open}`, UI. Trace RF-001–033, RNF-001–007, CS-001–009 via [contracts/transfer.md](contracts/transfer.md)/[data-model.md](data-model.md)/[quickstart.md](quickstart.md).

## Dependencies and gates

F001/F002/F007/F008. Windows Credential Manager is validated through a temporary real Windows round-trip; SMTP remains unavailable if that system API cannot be loaded. The manual Send to Kindle action remains available. SMTP server setup/authorization remain under the person's control; no actual external server/device is used in automated validation.
