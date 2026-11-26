# Pesquisa — F006 Imagens

## Decisões

- Pillow official `ImageOps.exif_transpose` normaliza orientação e remove tag de orientação; aplicar apenas a derivados antes de outras transformações.
- Raster allowlist e max pixels devem ser enforced antes de tornar imagem aceita; fechar streams explicitamente e processar uma imagem por vez.
- CBZ usa `zipfile` apenas como leitor: enumerar/validar names e atributos antes de acessar bytes; não confiar em `extractall`; extrair por streaming para staging próprio após validar path. Limites cumulativos incluem conteúdo expandido.
- Perfil 600×800, grayscale, white background, contain/no distortion, crop and double-page split off por default conforme spec; não mudar originais.
- Pillow 13.0.0 foi resolvido em `uv.lock` para Python 3.12. No ambiente Windows usado para esta feature, o runtime confirmou decoder JPEG, suporte WEBP e `ImageOps.exif_transpose`; os testes também transformam fixtures JPEG, PNG e WEBP.
- A versão e os recursos foram conferidos na [release oficial 13.0.0](https://pillow.readthedocs.io/en/latest/releasenotes/13.0.0.html), na [instalação binária oficial](https://pillow.readthedocs.io/en/stable/installation/basic-installation.html), na [documentação de WebP](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) e na [referência EXIF transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html). Nenhum decoder foi presumido sem verificação.

## Referências primárias

- [Pillow ImageOps / EXIF](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html)
- [Python 3.12 zipfile](https://docs.python.org/3.12/library/zipfile.html)
- [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Qt for Python QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)

## Pendências

Não há pendência de biblioteca no ambiente Python 3.12 validado. A confirmação visual da interface e a conferência do recorte/conteúdo ainda estão listadas para validação manual no quickstart. Nenhuma dependência de rede foi adicionada.
