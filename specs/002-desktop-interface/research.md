# Pesquisa — F002 Interface Desktop

## Decisões

- PySide6 Widgets com QMainWindow e stack de páginas como shell inicial; sem framework extra.
- Operação simulada potencialmente longa usa QObject movido a QThread e sinais queued; o objeto QThread vive na thread que o criou. I/O real não é parte de F002.
- Preferência tema é da configuração F001; fixtures permanecem identificadas e não se misturam com entidades reais.
- `pytest-qt` é dependência candidata somente se documentação/compatibilidade forem revistas e resolvidas no lock; não incluída por pressuposto.

## Referências primárias

- [Qt for Python: QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
- [Qt for Python: Threads and QObjects](https://doc.qt.io/qtforpython-6/overviews/qtdoc-threads-qobject.html)
- [Qt for Python: Signals and Slots](https://doc.qt.io/qtforpython-6/overviews/qtcore-signalsandslots.html)

## Pendências

Critério 200 ms depende do perfil Windows de referência, definido em implementação com medição automatizada. Sem pendência de produto.
