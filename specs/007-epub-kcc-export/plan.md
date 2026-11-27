# Plano de Implementação: F007 — Exportação EPUB e KCC

**Branch**: `007-epub-kcc-export` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e conformidade

Exportar localmente páginas processadas em EPUB por capítulo ou volume; suportar CBZ opcional, divisão nativa por limite, RTL/LTR e perfil. Writer EPUB próprio usa `zipfile` e `xml.etree.ElementTree`; decisão do usuário em 25/11/2026 evita incluir EbookLib/AGPL. A CLI KCC 13.0.4 é opcional, sempre escolhida explicitamente e validada pelo help real; gera MOBI para K810 (600×800) e KPW34 (1072×1448). Nenhum upload/envio e nenhum KCC empacotado. O teste físico continua como gate manual.

## Arquitetura e pipeline

`application.exports` valida seleção completa, metadados/idioma, ProcessedPages/Profile e plano de divisão para EPUB/CBZ. `domain.exports` define contratos imutáveis de plano e artefato. Adapters: writer EPUB próprio serializa XML/ZIP pela biblioteca padrão; validação estrutural e EPUBCheck 5.4.0; CBZ nativo por zipfile; `KccCliWriter` verifica help local da CLI 13.0.4 quando uma exportação MOBI começa, usa somente opções comprovadas, `subprocess` com argumentos separados e `shell=False`, timeout de 15 min, cancelamento com término após 3 s e stdout/stderr descartados sem log. Não há `which`, instalação ou execução automática.

Staging em destino local gerenciado: gerar, validar ZIP/EPUB, conferir recursos locais, ordem e metadados; medir tamanho final; dividir EPUB/CBZ só em limites capítulo/página. MOBI não oferece divisão por tamanho. Não sobrescrever arquivo existente sem confirmação. O KCC recebe apenas cópias PNG numeradas em um subdiretório do staging, e a publicação exige saída única com nome esperado, extensão `.mobi`, assinatura `BOOKMOBI`, tamanho e hash; falha/cancelamento remove staging e preserva origem. O histórico é gravado após publicação.

## Conteúdo e dados

Capítulos e páginas seguem ordem estável F004/F006. Volume só quando fornecido. Idioma obrigatório para EPUB/MOBI; solicitar usuário se ausente. Título é passado ao KCC e autor vazio quando ausente, para evitar seu valor padrão. Capa local preservada; ausência gera capa tipográfica neutra no EPUB. RTL default para novo mangá, registro por Export; KCC recebe `--manga-style` somente para RTL. CBZ não promete direção de reader. MOBI restringe perfil a K810/KPW34.

## Dependências, gates e riscos

F001–F006 provêm Export/profile/catalog/pages; F008 consolida resultado; F009 consome somente EPUB. O usuário autorizou o writer da biblioteca padrão; EbookLib permanece fora do projeto. EPUBCheck 5.4.0 foi executado. Help e conversões reais verificaram KCC 13.0.4 em dois perfis; KCC segue fora do bundle e a compatibilidade em Kindle físico permanece pendente.

Estrutura: `domain/exports`, `application/exports`, `infrastructure/exports/{epub,cbz,kcc,validation,staging}`, `presentation/qt/workers/export_worker.py`; aceitação em `tests/{unit,integration,security,acceptance}/exports`. Teste unitário de order/metadata/division; integrações com EPUB fixtures, EPUBCheck fixado, CBZ, fake KCC runner, timeout/cancel, failure after each write; manual Kindle route registra modelo, firmware, hash e transferência. Nunca executar KCC, SMTP ou dispositivo nesta etapa. Requisitos RF-001–032, RNF-001–007, CS-001–009 em [data-model.md](data-model.md), [contracts/export.md](contracts/export.md), [quickstart.md](quickstart.md).
