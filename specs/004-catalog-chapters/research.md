# Pesquisa — F004 Catálogo

- A regra de ordenação é local: comparar número fornecido como valor decimal; specials após numerados; usar ordem de fonte declarada e ID como estabilidade, sem inferir de title. Requisito e casos vêm da spec.
- IDs qualificados por provider/source persistem; lista visual nunca é identidade.
- Uma resposta de refresh só é publicada após validação do catálogo completo; erro tipado mantém snapshot anterior.
- Pydantic pode validar DTOs/fixtures externos se necessário; schema não substitui validação de domínio. `BaseModel.model_json_schema` gera draft 2020-12, mas F004 não precisa serializar schema no runtime.
- F003 bloqueia rede real; F004 só usa fixture e asset local.

Referências: [Pydantic JSON Schema](https://pydantic.dev/docs/validation/latest/concepts/json_schema/), [SQLAlchemy unit of work/session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [arquitetura integrada](../architecture-plan.md).

Sem novas dependências ou gate de produto.
