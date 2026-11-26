# Pesquisa — F007 EPUB/KCC

## Decisões

- A consulta em 25/11/2026 identifica EbookLib 0.21, publicado em 01/11/2026. O PyPI declara AGPL-3.0-or-later, Python >=3.10 e wheel universal; a release não tem provenance publicada. A página do repositório oficial também identifica AGPL-3.0.
- O checkout não tem arquivo `LICENSE` no root nem campo `project.license` em `pyproject.toml`. Em 25/11/2026, o usuário autorizou explicitamente alterar a F007 para um writer próprio com biblioteca padrão Python. Assim, EbookLib não será adicionado ao lock nem à distribuição; a especificação e o plano foram atualizados para registrar a mudança.
- O README oficial do EbookLib documenta escrita/leitura EPUB2/EPUB3 e exemplos de metadados, capa, TOC e spine. Essa evidência não demonstra que a versão 0.21 emita layout fixo; o projeto optou por gerar diretamente a estrutura conforme W3C com `zipfile` e `xml.etree.ElementTree`, sem copiar implementação ou API da biblioteca.
- EPUB 3.3 é recomendação W3C vigente (13/01/2026); define layout `pre-paginated`, dimensões do viewport e `page-progression-direction` RTL/LTR. EPUBCheck 5.4.0 é a versão oficial de produção consultada; sua release informa validação EPUB 2/3 e suporte à recomendação candidata EPUB 3.4. A implementação deve fixar essa versão no roteiro e só publicar sem erros de conformidade.
- EPUB 3.3 define metadata, reading order/spine e page progression direction. Idioma/identifier/capa/TOC devem ser validados estruturalmente. EPUBCheck é ferramenta de aceitação, versão fixada e registrada.
- KCC permanece instalação externa da pessoa usuária. Antes de argumentos, identificar versão concreta e evidência dessa instalação; nada de CLI montado por exemplos de outra versão. O código-fonte oficial atual contém consultas de versão/anúncio na interface gráfica; como não há binário instalado validado neste ambiente, nenhum help, CLI, conversão ou execução de KCC foi iniciado. Binário nunca é baixado pelo app.
- Processo é lançado sem shell e com argumentos individualizados; stdout/stderr podem conter dados: capturar sem registrá-los integralmente. Tempo/cancel vêm da spec.
- CBZ usa imagens processadas, nomes ordenáveis e não declara direção universal.

## Fontes primárias

- [EPUB 3.3 (W3C)](https://www.w3.org/TR/epub-33/)
- [EPUBCheck (W3C/DAISY)](https://github.com/w3c/epubcheck)
- [EbookLib 0.21 no PyPI — release, requisitos e licença](https://pypi.org/project/EbookLib/0.21/)
- [EbookLib official repository/tutorial](https://github.com/aerkalov/ebooklib)
- [KCC official repository](https://github.com/ciromattia/kcc)
- [Python subprocess](https://docs.python.org/3.12/library/subprocess.html)
- [EPUBCheck releases](https://github.com/w3c/epubcheck/releases)

## Gates e pendências

`B007-EBOOKLIB-LICENSE` foi resolvido pela autorização explícita para não usar EbookLib e alterar RF-010. `B007-EPUB-FXL` continua aberto até o writer produzir um pacote aprovado pelo EPUBCheck 5.4.0. `B007-KCC-NETWORK` e `B007-KCC-CAPABILITY` continuam abertos para a instalação concreta de KCC. Nenhuma versão/help/conversão KCC foi executada, não houve teste físico de Kindle e não se declara Send to Kindle fixed layout compatível.
