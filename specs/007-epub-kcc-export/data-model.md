# Modelo de Dados — F007

| Tipo | Dados/invariantes |
|---|---|
| `ExportPlan` | selection IDs, validated pages/profile snapshot, language, direction, grouping, format, size limit, destination, adapter capability; imutável ao iniciar. |
| `ExportJob` | estado/progresso/cancelamento, staging ID, erro categorizado, início/fim; terminal não reabre. |
| `ExportPackage` | path gerenciado, formato real, chapter/page IDs em ordem, checksum, bytes, part number, validation status. |
| KCC path/capability | Caminho é escolhido na UI por tentativa e não é persistido. O adaptador verifica help local da CLI 13.0.4; a fixture/proveniência da validação real está em `tests/fixtures/kcc/`. |
| `ExportValidationReport` | validator/version, errors/warnings, metadata, referenced resources, external refs/scripts. |
| `ManualDeviceTest` | file hash, output/adapter version, Kindle model/gen, firmware, route USB/Send to Kindle, criteria/results. |

EPUB per chapter usa Chapter ID; grouped output exige volume explicitamente informado. Locale ausente solicita escolha válida para EPUB/MOBI. MOBI aceita apenas K810 (600×800) e KPW34 (1072×1448) e não aceita limite de tamanho. Identifier do pacote é exclusivo, nunca ISBN. Parts medem bytes finais, mantêm páginas inteiras e não truncam uma página acima do limite. EPUB/CBZ/MOBI persistem seus artefatos via F008 após publicação atômica.

Estados: pending → running → validating → completed; failed/cancelled/interrupted são explícitos. `completed` requer pacote publicado + validação; manual device test é evidência separada.
