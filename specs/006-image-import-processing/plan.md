# Plano de Implementação: F006 — Importação e Processamento de Imagens

**Branch**: `006-image-import-processing` | **Data**: 2026-11-25 | **Spec**: [spec.md](spec.md)

## Objetivo e conformidade

Importar fontes locais autorizadas (pastas/CBZ) para área gerenciada, pré-visualizar ordem natural e produzir derivados Kindle Básico 10 600×800 sem esticar/cortar por padrão. Originais permanecem byte a byte imutáveis. Sem rede/transferência. Operações ZIP, disco e Pillow são worker cancelável; publishing de lote é atômico/recuperável.

## Arquitetura e fluxo

`application.images` coleta seleção UI, valida autorização local e planeja import batch. `infrastructure.archive` enumera/verifica todos membros antes de extrair; não confia em caminho do ZIP, nunca usa extract-all; streaming para staging com contadores. `infrastructure.images` usa Pillow para decode, `ImageOps.exif_transpose`, alpha sobre branco, grayscale 8-bit PNG, proporcional contain em 600×800 menos margens, branco no espaço residual. `domain.images` guarda source fingerprint, ordem e derivative metadata; F008 persiste entidades via repositório. `presentation.qt` mostra preview e progresso via worker signals.

Entrada allowlist JPEG/PNG/WEBP; sem SVG/executáveis. Limites cumulativos da spec: 10.000 entradas, 5.000 imagens, 25 MiB/imagem, 2 GiB/origem, 50 MP/imagem, contados durante leitura/decode. Rejeitar traversal absoluto/UNC/drive/`..`, link/special entries e colisões após normalização Windows. CBZ encrypted recusa; sem contornar senha. Falha de uma imagem cancela lote antes de publicação. Reimport idempotente por normalized relative path + checksum; mesma imagem em outra posição/ID alerta sem merge.

## Processamento

Default margem zero, crop off, double-page split off, RTL. Cropping é opt-in, prévia/confirm/desfazer. Página dupla exige seleção/confirmação por imagem; right panel primeiro em RTL, left first em LTR; persistir relação do derivado com source Page. Nenhuma mudança regrava original. Derived content tem profile/parameters snapshot. Cancelamento remove só staging próprio; transação de F008 publica tudo ou reconcilia lote incompleto.

## Estrutura e testes

```text
application/images/{scan,plan_import,import,preview,process,recover}.py
domain/images/{source_fingerprint,processed_page,processing_profile}.py
infrastructure/{archive,images}/
presentation/qt/{workers,image_preview}/
tests/{unit,integration,security,ui}/images/
```

Testar formatos, EXIF, transparência, grayscale, ratio, natural sort, limites abaixo/no/acima, traversal/UNC/drive/link/name collision, encrypted archive, arquivo corrompido, disco cheio, cancel points, atomicity, orientation/order of double pages, cropping disabled/reversible and source hash unchanged. Mapear RF-001–029, RNF-001–008, CS-001–010. [Contracts](contracts/image-processing.md), [model](data-model.md), [quickstart](quickstart.md).

## Dependências e riscos

F001/F002; F003 policy boundary (no access/source bypass; F006 itself is offline); F004 IDs/order; F005 Page limits/originals and recovery. Pillow support for WEBP/JPEG/PNG/EXIF in resolved Windows build must be tested. Zip bombs are mitigated by streaming counters, no full expanded archive in memory. Profile and schema shared with F011/F008. No code/test executed.
