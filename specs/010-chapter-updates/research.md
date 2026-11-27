# Pesquisa — F010 Atualizações

- Scheduling is in-process only: QTimer announces due work to application, which creates worker; timer does no provider calls in Qt thread. On close all active jobs cancel/persist; no Windows service/background agent scope.
- Each `get_chapters` use requires its own permission/capability; an API metadata license cannot be treated as download permission. Rate limits and minimum interval come from provider docs; absent evidence disables remote polling.
- Compare stable provider-qualified Chapter IDs, not title/position; only valid full snapshot and notifications commit together. New chapter notice is local and independent from download/send.
- B003 prevents live provider; test with fake clock/fixture only.

References: [Qt QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html), [Qt QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html), [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/).

No new dependency justified; periodic behavior uses Qt timer + existing provider/repository ports.

## Revisão de fonte pública — 2026-11-26

A documentação oficial da [MangaDex API](https://gitlab.com/mangadex-pub/mangadex-api-docs/-/raw/main/index.md) informa que a API pública/gratuita só pode ser usada por projetos que cumpram condições como atribuir crédito e não executar anúncios/serviços pagos. O checkout não define o modelo de distribuição/monetização do aplicativo nem possui uma decisão de atribuição da fonte. A MangaDex, portanto, não foi habilitada como fonte; a policy pública não equivale a uma autorização irrestrita para todos os usos do produto.

F010 continua bloqueada até uma fonte específica e seu escopo serem aprovados e registrados: consulta de metadados, termos, limite e intervalo mínimo, atribuição, identidade estável, retenção/removal requests e modo de distribuição do Manga to Kindle. A implementação permanece sem tráfego remoto e sem scheduler de produto; a fixture F003/F004 é somente demonstração/teste.
