# Pesquisa — F006 Imagens

## Decisões

- Pillow official `ImageOps.exif_transpose` normaliza orientação e remove tag de orientação; aplicar apenas a derivados antes de outras transformações.
- Raster allowlist e max pixels devem ser enforced antes de tornar imagem aceita; fechar streams explicitamente e processar uma imagem por vez.
- CBZ usa `zipfile` apenas como leitor: enumerar/validar names e atributos antes de acessar bytes; não confiar em `extractall`; extrair por streaming para staging próprio após validar path. Limites cumulativos incluem conteúdo expandido.
- Perfil 600×800, grayscale, white background, contain/no distortion, crop and double-page split off por default conforme spec; não mudar originais.
- Pillow fica como dependência runtime F006; versão/suporte WEBP e wheels Windows/Python devem ser confirmados no lock escolhido. Nenhuma versão suposta.

## Referências primárias

- [Pillow ImageOps / EXIF](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html)
- [Python 3.12 zipfile](https://docs.python.org/3.12/library/zipfile.html)
- [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
- [Qt for Python QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)

## Pendências

Wheel Pillow/Python/Windows e decoder WEBP serão provados no ambiente `uv` quando F001 existir. Nenhuma dependência de rede.
