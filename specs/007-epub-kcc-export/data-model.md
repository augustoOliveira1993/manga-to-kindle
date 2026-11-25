# Modelo de Dados — F007

| Tipo | Dados/invariantes |
|---|---|
| `ExportPlan` | selection IDs, validated pages/profile snapshot, language, direction, grouping, format, size limit, destination, adapter capability; imutável ao iniciar. |
| `ExportJob` | estado/progresso/cancelamento, staging ID, erro categorizado, início/fim; terminal não reabre. |
| `ExportPackage` | path gerenciado, formato real, chapter/page IDs em ordem, checksum, bytes, part number, validation status. |
| `KccInstallation` | caminho local, versão/capacidades comprovadas, evidência/tempo; não instala nem executa automaticamente. |
| `CapabilityEvidence` | feature (format/arg/profile), fonte da evidência, versão binária, consentimento se a verificação pode conectar. |
| `ExportValidationReport` | validator/version, errors/warnings, metadata, referenced resources, external refs/scripts. |
| `ManualDeviceTest` | file hash, output/adapter version, Kindle model/gen, firmware, route USB/Send to Kindle, criteria/results. |

EPUB per chapter usa Chapter ID; grouped output exige volume explicitamente informado. Locale ausente solicita escolha válida. Identifier do pacote é exclusivo, nunca ISBN. Parts medem bytes finais, mantêm páginas inteiras e não truncam uma página acima do limite. IDs/metadata persistem via F008 após publicação atômica.

Estados: pending → running → validating → completed; failed/cancelled/interrupted são explícitos. `completed` requer pacote publicado + validação; manual device test é evidência separada.
