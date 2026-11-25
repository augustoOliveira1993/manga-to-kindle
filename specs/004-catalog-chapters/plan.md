# Plano de Implementação: F004 — Catálogo e Capítulos

**Branch**: `004-catalog-chapters` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e conformidade

Integrar a tela de consulta à porta F003 e apresentar metadados efetivamente fornecidos, capítulos determinísticos, seleção por identidade/intervalo e atualização recuperável. Só fixtures nesta feature; B003 impede rede real. Sem inferir metadata nem baixar capa.

## Arquitetura

`application.catalog` chama caso de uso F003 no worker; valida resposta completa; mapeia erros tipados a view states PT-BR. `domain.catalog` expõe `CatalogSnapshot`, `ChapterOrderKey`, `ChapterSelection`. F004 não duplica provider, URL validation, persistence layer ou widget; F008 é proprietário de repositórios e busca local. Atualização lê lista nova para staging, valida IDs/métodos/ordem e publica transação completa; falha ou cancelamento retém última versão válida. Capa fica placeholder ou asset local fixture; URL remota não é carregada.

Ordenar usando campo numérico explicitamente fornecido, nunca extração textual: numeric ascending, decimais, depois specials; fonte sequence para empate quando presente, stable ID como desempate final. IDs são provider/source-qualified. Seleção é set de IDs; intervalo inclusivo sobre ordem de apresentação, inclusive especiais. Em refresh, IDs ainda existentes mantêm seleção, novos iniciam desmarcados, ausentes saem dela.

## Dados, testes e riscos

Opcionalidade: autor/capa/idioma/volume/disponibilidade ficam None/desconhecidos quando ausentes; título/ID inválido causa resultado rejeitado. Atualização deve gravar metadados e capítulos em transação/repository unit of work sem merge parcial. Contratos de UI e modelo em [contracts/catalog.md](contracts/catalog.md)/[data-model.md](data-model.md).

Testes: fixtures com dados ausentes/decimais/especiais/IDs repetidos; equivalência numérica, stable tie break, intervalos invertidos/inclusivos, refresh com seleções preservadas, erro de provider após snapshot anterior e proibição de rede. Mapear RF-001–020, RNF-001–007, CS-001–007. Riscos: número parseado de título, refresh parcial e capa remota disparar request; validar campo explícito, staging/transação e origem local por teste.

## Dependências e gates

F001 tipos/persistência e F002 tela; F003 provider fixture, erros/capabilities/URL safety. F005 consome capítulo selecionado depois; F008 consolida persistência. Nenhuma fonte real está autorizada; fixture de falha simula indisponibilidade sem socket. Sem bloqueio do catálogo fixture. A suite não foi executada.
