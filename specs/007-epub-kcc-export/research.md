# Pesquisa — F007 EPUB/KCC

## Decisões

- Padrão local é EPUB nativo conforme spec, mas `EbookLib` só pode entrar no lock/artefato após aprovação da licença AGPL-3.0+ e compatibilidade comprovada. A página atual do projeto e PyPI informa essa licença.
- Uma capacidade fixed-layout exige recursos documentados da versão travada, inspeção de output e EPUBCheck sem erros. Não improvisar item APIs/styles no EbookLib.
- EPUB 3.3 define metadata, reading order/spine e page progression direction. Idioma/identifier/capa/TOC devem ser validados estruturalmente. EPUBCheck é ferramenta de aceitação, versão fixada e registrada.
- KCC permanece instalação externa da pessoa usuária. Antes de argumentos, identificar versão concreta e evidência dessa instalação; nada de CLI montado por exemplos de outra versão. README KCC relata version/announcement check na inicialização: probe/execution exige opt-in por execução ou offline comprovado. Binário nunca é baixado pelo app.
- Processo é lançado sem shell e com argumentos individualizados; stdout/stderr podem conter dados: capturar sem registrá-los integralmente. Tempo/cancel vêm da spec.
- CBZ usa imagens processadas, nomes ordenáveis e não declara direção universal.

## Fontes primárias

- [EPUB 3.3 (W3C)](https://www.w3.org/TR/epub-33/)
- [EPUBCheck (W3C/DAISY)](https://github.com/w3c/epubcheck)
- [EbookLib license (PyPI)](https://pypi.org/project/EbookLib/0.21/)
- [EbookLib official repository/tutorial](https://github.com/aerkalov/ebooklib)
- [KCC official repository](https://github.com/ciromattia/kcc)
- [Python subprocess](https://docs.python.org/3.12/library/subprocess.html)

## Gates e pendências

`B007-EBOOKLIB-LICENSE`, `B007-EBOOKLIB-FXL`, `B007-KCC-NETWORK`, `B007-KCC-CAPABILITY` seguem em aberto. A pesquisa confirma os bloqueios e não os remove. O planejamento não executou KCC/help, não testou Kindle e não declara Send to Kindle fixed layout compatível.
