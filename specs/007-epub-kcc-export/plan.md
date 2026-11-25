# Plano de Implementação: F007 — Exportação EPUB e KCC

**Branch**: `007-epub-kcc-export` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e conformidade

Exportar localmente páginas processadas em EPUB por capítulo ou volume; suportar CBZ opcional, divisão por limite, RTL/LTR e perfil. KCC é adaptador externo opcional, sempre escolhido explicitamente; nenhum upload/envio. Build segue constituição: workers, cancelamento, atomicidade, logs sem título/caminho/conteúdo, dependências e CLI versionadas/verificadas. Gates F007 mantidos.

## Arquitetura e pipeline

`application.exports` valida seleção completa, metadados/idioma, ProcessedPages/Profile, capacidade/gates e plano de divisão. `domain.exports` define `ExportPlan`, `ExportJob`, `PackageManifest` e status. Adapters: gerador nativo EPUB (EbookLib somente após licença + capacidade fixed layout comprovadas); CBZ nativo por zipfile; `KccAdapter` executa binário escolhido/configurado via `subprocess` argumentos separados, `shell=False`, cwd/env controlados, timeout default 15 min (faixa 1–60), cancel termina gracefully e force após 5 s, capture output sanitizado. `KccCapabilityProbe` não executa processo na detecção passiva; qualquer consulta à versão/help que possa conectar pede opt-in por execução, ou requer modo offline de instalação verificado. Sem `which` seguido de execução automática.

Staging em destino local gerenciado: gerar, validar ZIP/EPUB, conferir todos recursos locais, ordem, metadata, sem script ou refs externas; medir tamanho final; dividir só em limites capítulo/página, preservando página inteira e sem exceder. Se página única ultrapassa, falha. Não sobrescrever arquivo existente sem confirmação. `os.replace` após validar; persistir Export pronto apenas após rename. KCC sai em staging isolado e o artefato fica separado até validação/capability validada; nunca pode substituir um EPUB válido.

## Conteúdo e dados

Capítulos e páginas seguem ordem estável F004/F006. Volume só quando fornecido. Idioma obrigatório no EPUB 3; solicitar usuário se ausente. Título e autor escapados; autor omitido se ausente. Capa local preservada; ausência gera capa tipográfica neutra marcada como gerada. RTL default para novo mangá, registro por Export. Fixed layout com dimensões do perfil somente após provar API e validar com EPUBCheck. CBZ não promete direção de reader; KCC direction só se versão confirma.

## Dependências, gates e riscos

F001–F006 provêm Export/profile/catalog/pages; F008 persiste resultado; F009 consome após validação. Gates: `B007-EBOOKLIB-LICENSE` AGPL review antes de dependência/distribuição; `B007-EBOOKLIB-FXL` prova fixed layout via API documentada+EPUBCheck; `B007-KCC-NETWORK` exige opt-in de rede por execução ou offline verificável; `B007-KCC-CAPABILITY` bloqueia formatos/opções sem confirmação da versão local. Não substituir EbookLib por outra biblioteca silenciosamente nem inventar argumento.

Estrutura: `domain/exports`, `application/exports`, `infrastructure/exports/{epub,cbz,kcc,validation,staging}`, `presentation/qt/workers/export_worker.py`; aceitação em `tests/{unit,integration,security,acceptance}/exports`. Teste unitário de order/metadata/division; integrações com EPUB fixtures, EPUBCheck fixado, CBZ, fake KCC runner, timeout/cancel, failure after each write; manual Kindle route registra modelo, firmware, hash e transferência. Nunca executar KCC, SMTP ou dispositivo nesta etapa. Requisitos RF-001–032, RNF-001–007, CS-001–009 em [data-model.md](data-model.md), [contracts/export.md](contracts/export.md), [quickstart.md](quickstart.md).
