# Pesquisa — F010 Atualizações

- Scheduling is in-process only: QTimer announces due work to application, which creates worker; timer does no provider calls in Qt thread. On close all active jobs cancel/persist; no Windows service/background agent scope.
- Each `get_chapters` use requires its own permission/capability; an API metadata license cannot be treated as download permission. Rate limits and minimum interval come from provider docs; absent evidence disables remote polling.
- Compare stable provider-qualified Chapter IDs, not title/position; only valid full snapshot and notifications commit together. New chapter notice is local and independent from download/send.
- B003 prevents live provider; test with fake clock/fixture only.

References: [Qt QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html), [Qt QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html), [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/).

No new dependency justified; periodic behavior uses Qt timer + existing provider/repository ports.
