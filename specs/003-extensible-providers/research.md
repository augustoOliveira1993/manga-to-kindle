# Pesquisa — F003 Provedores

## Decisões técnicas

- Fixture handler intercepta `https://fixture.invalid/...` localmente antes de resolver nome; não há fallback à internet.
- HTTPX é candidato futuro: docs confirmam timeouts/pool configuráveis e redirects desligados por padrão. O uso real exige autorização verificada e regra própria para cada request/hop.
- HTTPX não garante que DNS validado e socket conectado usem o mesmo IP; não declarar SSRF protegido só por validar resolução antecipada. Sem adapter seguro comprovado, mantém-se bloqueio.
- BeautifulSoup4 continua condicional; não instalar até scraping/parser ser explicitamente autorizado para uma fonte documentada.
- Retry/rate limit têm origem na política de cada provedor, nunca em defaults de cliente.

## Referências primárias

- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [HTTPX resource limits](https://www.python-httpx.org/advanced/resource-limits/)
- [HTTPX redirects](https://www.python-httpx.org/compatibility/#redirects)
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Beautiful Soup docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — não usada por fixtures.

## Bloqueio

`B003-REAL-SOURCE`: nenhuma fonte identificada com autorização verificável para baixar o conteúdo pretendido. Não incluir MangaDex ou outra fonte como real; uma futura integração demanda prova/revisão dos termos e especificação própria.

## Procedimento para reavaliar o bloqueio

Antes de qualquer provider de produção, registrar fonte e páginas oficiais dos termos aplicáveis; confirmar expressamente que consulta, armazenamento local e uso pretendido são autorizados; descrever limites de taxa, atribuição, licença, remoção e condições de encerramento; revisar destinos, redirects e riscos SSRF; e obter aprovação humana para o escopo concreto. Sem todos esses itens, manter `B003-REAL-SOURCE`, `download_authorized=False` e testes sem tráfego externo. Uma licença permissiva do código de uma biblioteca não autoriza baixar conteúdo hospedado por terceiros.
