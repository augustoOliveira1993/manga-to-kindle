# Pesquisa — F007 EPUB/KCC

## Decisões

- A consulta em 25/11/2026 identifica EbookLib 0.21, publicado em 01/11/2026. O PyPI declara AGPL-3.0-or-later, Python >=3.10 e wheel universal; a release não tem provenance publicada. A página do repositório oficial também identifica AGPL-3.0.
- O checkout não tem arquivo `LICENSE` no root nem campo `project.license` em `pyproject.toml`. Em 25/11/2026, o usuário autorizou explicitamente alterar a F007 para um writer próprio com biblioteca padrão Python. Assim, EbookLib não será adicionado ao lock nem à distribuição; a especificação e o plano foram atualizados para registrar a mudança.
- O README oficial do EbookLib documenta escrita/leitura EPUB2/EPUB3 e exemplos de metadados, capa, TOC e spine. Essa evidência não demonstra que a versão 0.21 emita layout fixo; o projeto optou por gerar diretamente a estrutura conforme W3C com `zipfile` e `xml.etree.ElementTree`, sem copiar implementação ou API da biblioteca.
- EPUB 3.3 é recomendação W3C vigente (13/01/2026); define layout `pre-paginated`, dimensões do viewport e `page-progression-direction` RTL/LTR. EPUBCheck 5.4.0 é a versão oficial de produção consultada; sua release informa validação EPUB 2/3 e suporte à recomendação candidata EPUB 3.4. A implementação deve fixar essa versão no roteiro e só publicar sem erros de conformidade.
- EPUB 3.3 define metadata, reading order/spine e page progression direction. Idioma/identifier/capa/TOC devem ser validados estruturalmente. EPUBCheck é ferramenta de aceitação, versão fixada e registrada.
- A CLI oficial KCC v13.0.4 foi baixada manualmente para pasta temporária de validação, sem inclusão no repo ou no bundle. `tool_cli_c2e_13.0.4_AMD64.exe` tinha SHA-256 `AC245FE431063875CBE5290731094356655ACCCE3217048AE3ECB7E63F210C22` e assinatura Authenticode válida de SignPath Foundation (thumbprint `E4BF93A16549F881534568592D65FE1222C88630`). A ajuda integral capturada está em `tests/fixtures/kcc/13.0.4-windows-amd64-help.txt`; origem e hashes estão no JSON adjacente.
- A ajuda real confirma `--profile`, `--format MOBI`, `--cropping`, `--output`, `--title`, `--filename`, `--author`, `--language` e `--manga-style`. Conversões reais de três imagens sintéticas completaram com `K810` (600×800) e `KPW34` (1072×1448), produzindo `.mobi` com `BOOKMOBI` no byte 60; também foi criada saída EPUB. A aplicação aceita apenas MOBI nesses perfis; tentativa de saída MOBI com perfil genérico falhou no próprio KCC, portanto outros perfis continuam bloqueados.
- O binário oficial c2e executou via `--help` e conversões locais; revisão do entrypoint/função de conversão oficial indica verificação local de dependências no caminho CLI. O app não usa a GUI KCC, cuja interface tem consultas de versão/anúncio. Não foi feita inspeção de tráfego de rede do processo; futuras versões permanecem rejeitadas até nova revisão. Binário nunca é baixado pelo app.
- Processo é lançado sem shell e com argumentos individualizados; stdout/stderr são descartados sem log. Timeout é 15 min, cancel tenta encerrar até 3 s e depois força. Cópias do staging protegem páginas originais.
- CBZ usa imagens processadas, nomes ordenáveis e não declara direção universal.

## Fontes primárias

- [EPUB 3.3 (W3C)](https://www.w3.org/TR/epub-33/)
- [EPUBCheck (W3C/DAISY)](https://github.com/w3c/epubcheck)
- [EbookLib 0.21 no PyPI — release, requisitos e licença](https://pypi.org/project/EbookLib/0.21/)
- [EbookLib official repository/tutorial](https://github.com/aerkalov/ebooklib)
- [KCC official repository](https://github.com/ciromattia/kcc)
- [KCC v13.0.4 official Windows release](https://github.com/ciromattia/kcc/releases/tag/v13.0.4)
- [Python subprocess](https://docs.python.org/3.12/library/subprocess.html)
- [EPUBCheck releases](https://github.com/w3c/epubcheck/releases)

## Gates e pendências

`B007-EBOOKLIB-LICENSE` foi resolvido pela autorização explícita para não usar EbookLib e alterar RF-010. `B007-EPUB-FXL` continua aberto até o writer produzir um pacote aprovado pelo EPUBCheck 5.4.0. `B007-KCC-NETWORK` e `B007-KCC-CAPABILITY` continuam abertos para a instalação concreta de KCC. Nenhuma versão/help/conversão KCC foi executada, não houve teste físico de Kindle e não se declara Send to Kindle fixed layout compatível.
