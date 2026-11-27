# Pesquisa — F003 Provedores

## Decisão autorizada — 2026-11-27

A pessoa usuária autorizou: (1) consultas pontuais de metadados à Next Digital Library da
National Diet Library (NDL); (2) download local, iniciado por seleção explícita, de item
individual pertencente ao acervo marcado Public Domain Mark; (3) nenhuma atualização
periódica ou contínua. A autorização não cobre outros catálogos, distribuição do conteúdo,
acesso em lote sem seleção nem conteúdo cuja inclusão no acervo PDM não tenha sido
confirmada.

## Evidência e limites da fonte

- A [página oficial do serviço NDL](https://lab.ndl.go.jp/service/tsugidigi/tsugidigi_en/)
  descreve Next Digital Library como acervo experimental de livros antigos/raros com
  materiais e dados Public Domain Mark. Os avisos PDM/CC0 devem ser preservados. Consulta
  contínua requer contato com a NDL; a aplicação não implementa periodicidade.
- A [documentação oficial da API](https://lab.ndl.go.jp/service/tsugidigi/apiinfo/)
  documenta busca/detalhe de livros e imagens IIIF. Os exemplos incluem o padrão de URL
  `/api/iiif/{PID}/R0000028/full/full/0/default.jpg`.
- Em 2026-11-27, com autorização limitada já obtida, uma consulta pontual real ao endpoint
  `/dl/api/book/search` retornou `北斎漫画`, volume `５編` (1878), PID `851650`, 33 páginas.
  O endpoint de detalhe confirmou os metadados; a API não devolve campo de direitos, então
  a indicação PDM deriva da inclusão do item no corpus descrito nos termos da NDL, não de
  uma flag por registro.
- A documentação não publica cota numérica de requisições/minuto. A aplicação impõe um
  intervalo mínimo de 60 segundos entre consultas de metadados e até 12 requisições IIIF
  por minuto. Esses são limites locais, sem atribuí-los à NDL.
- O smoke de 27/11/2026 confirmou que a página 1 retorna JPEG diretamente; páginas 21 e 29
  retornaram HTTP 307 do endpoint IIIF oficial para o host exato
  `dss-r4-prod-contents-download.s3.amazonaws.com`. O bucket respondeu HTTP 200 com bytes
  JPEG e `binary/octet-stream`; o aplicativo valida cada redirect/IP/TLS e só usa fallback
  `image/jpeg` para uma referência `.jpg`, seguida de verificação de assinatura e decode.
  O download completo F005 terminou com 33/33 arquivos no perfil temporário de QA.

## Implementação segura

- `NdlProvider` aceita somente `https://lab.ndl.go.jp/dl/book/<PID>` e consulta um registro
  de metadados por ação explícita no worker de catálogo.
- O transporte padrão da biblioteca valida host/porta/esquema, resolve A/AAAA uma vez,
  recusa respostas DNS mistas ou não globais, conecta diretamente a IP validado, mantém SNI
  e valida o certificado do host atual. Ele não usa proxies ambientais. Todo redirect exige
  HTTPS e host exato aprovado, tem IP e TLS revalidados, detecta loops e termina em até cinco
  saltos; o bucket S3 de entrega da NDL é o único host adicional autorizado.
- O provider cria referências IIIF apenas para páginas do item cujo metadado foi obtido.
  F005 revalida destino, MIME, assinatura/tamanho raster e persiste atomicamente.
- `periodic_catalog_updates_authorized=False`. A F010 permanece bloqueada para NDL.
- A fixture `fixture.invalid` segue offline, sintética e sem autorização de download.

## Referências adicionais

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Python `http.client`](https://docs.python.org/3/library/http.client.html)
- [Python `ssl`](https://docs.python.org/3/library/ssl.html)

## Bloqueios restantes

`B003-REAL-SOURCE` continua para MangaDex e demais provedores, uso contínuo/periódico,
itens fora do corpus PDM e qualquer distribuição de conteúdo. Não inferir que o catálogo
da NDL represente mangas modernos ou uma coleção completa de capítulos.
