# Pesquisa — F011 Perfis

## Decisões

- Device profiles are data with source generation and version, not claims of physical detection; Basic 8/10 and Paperwhite 10 remain distinct factory profiles.
- Official manufacturer material cited by spec supports 600×800 portrait for Basic (reported 800×600 landscape axis), 167 ppi/16 gray, and Paperwhite 10 1072×1448 portrait/300 ppi/16 gray. Re-check links and product generation before implementation; do not generalize later Paperwhite.
- Cache cleanup is allowlist by manifest/status and managed path, no broad directory deletion; process expired first then LRU under spec's configurable quota.
- Quality support is output capability, not profile assumption: 1–100 only where encoder supports; PNG is not applicable.
- Profile snapshots preserve parameters for in-flight jobs and exports; config migrations use explicit default only for fields absent in old records.

## Referências oficiais

- [Amazon Kindle Basic 10 safety/specification](https://digprjsurvey.amazon.com/csad/help/node/GMP9ALGUF96MMD8A)
- [Amazon Basic 8 user guide](https://images-na.ssl-images-amazon.com/images/I/91r6awkZtRS.pdf)
- [Amazon Paperwhite user guide](https://images-na.ssl-images-amazon.com/images/I/81-sqj3b5bS.pdf)
- [Amazon Paperwhite 10th Generation](https://images-na.ssl-images-amazon.com/images/I/812Wt8KavHS.pdf)
- [Amazon identify Kindle model](https://digprjsurvey.amazon.com/csad/help/node/GK33S847NN4V6Y83)
- [SQLAlchemy 2 session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)

Nenhuma nova runtime dependency é necessária.
