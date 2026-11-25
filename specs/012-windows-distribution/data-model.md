# Modelo de Dados — F012

## Escopo e Propriedade

Os registros de build/release descritos aqui são documentos da distribuição. Eles não são gravados na base SQLite de biblioteca. O SQLite continua pertencendo ao aplicativo conforme F001/F008, e instalador, updater manual e PyInstaller não manipulam suas tabelas.

As entidades persistidas do produto — Manga, Chapter, Page, DownloadJob, DeviceProfile e Export — são definidas por F001 e pelas features consumidoras. F012 exige que atualizações as preservem; não redefine suas colunas.

## Tipos e Regras Comuns

- Todos os identificadores de código e propriedades internas serão em inglês; rótulos de interface/instalador serão pt-BR.
- **ProductVersion**: SemVer estável MAJOR.MINOR.PATCH; prerelease deve ter identificador explícito. A regra para metadado PE de quatro componentes deve derivar da versão canônica, sem números inventados.
- **Sha256**: exatamente 64 dígitos hexadecimais minúsculos.
- **CommitId**: identificador completo do commit de origem; nenhum caminho de usuário, token, e-mail ou conteúdo de livro acompanha a proveniência.
- **TargetPair**: Windows 10 ou Windows 11 mais arquitetura x64, ARM64 ou x86. A lista permitida no artefato deve ser subconjunto da matriz aprovada. A aprovação dessa matriz continua pendente (B012-ARCH-MATRIX).
- Paths serializados são relativos ao pacote ou raiz de dados. É proibido registrar caminhos absolutos da máquina do builder como destino/runtime de usuário.
- Componentes distribuídos precisam de nome, versão, origem e licença/identificador confirmados; unknown ou gate pendente bloqueia a publicação.

## ReleaseManifest

Documento JSON versionado, validado com modelo Pydantic v2 e descrito pelo schema em [contracts/release-manifest.schema.json](contracts/release-manifest.schema.json).

| Campo | Tipo | Validação/finalidade |
|---|---|---|
| schema_version | string | Versão do schema do manifest; permite evolução sem interpretar formato desconhecido. |
| product | objeto | Nome, versão SemVer, descrição e publisher/copyright somente quando confirmados. |
| source | objeto | Commit completo, hash de uv.lock e revisão do arquivo de spec; fixa a proveniência do código. |
| toolchain | objeto | Python patch, uv, PyInstaller e imagem/identidade do Windows usados no build; versões resolvidas, não intervalos. |
| target_pairs | lista de TargetPair | Par Windows/arquitetura declarado para cada artefato; não inclui combinação não aprovada/testada. |
| bundle | objeto | Formato (portable-archive ou inno-installer), modo PyInstaller (onedir), raiz lógica e nome de artefato. |
| components | lista de PackagedComponent | Dependências/runtime/recurso efetivamente empacotado com versão, licença, origem e aviso associado. |
| artifacts | lista de ArtifactReference | Nome, formato e par-alvo de cada saída planejada; o hash final não fica dentro do manifest de insumos. Bundle diretório é entregue como arquivo de distribuição com digest calculável. |

O manifest normalizado representa insumos e composição. Timestamp de execução, digest de cada saída e estado dos gates ficam em ArtifactAttestation para que a comparação de dois builds não seja contaminada por dados variáveis. A atestação não substitui o manifest.

## PackagedComponent / ThirdPartyNotice

Cada componente Python direto/transitivo, runtime, plugin Qt, fonte, ícone derivado ou arquivo redistribuído aparece no inventário. KCC e navegador ausentes do pacote padrão são registrados como opcionais/externos apenas na documentação; não aparecem como empacotados.

| Campo | Tipo | Regra |
|---|---|---|
| name, version | string | Identidade e versão exatas do componente. |
| source_url | URI | Origem oficial ou registrador/origem do pacote. |
| license_id | string ou null | Identificador SPDX quando verificável; licença desconhecida é gate, não valor de aprovação. |
| copyright | string ou null | Texto confirmado pelo projeto/licença. |
| notice_path | path relativo ou null | Caminho de texto/aviso entregue no bundle; obrigatório quando a licença exigir. |
| category | enum | runtime, python-package, qt-plugin, resource ou native-library. |
| included | boolean | Distingue o que está dentro do artefato; nenhum opcional externo é incluído implicitamente. |

Os avisos/textos integrais exigidos são copiados para THIRD-PARTY-NOTICES. SBOM CycloneDX não substitui notices ou revisão legal.

## ArtifactAttestation

Uma atestação é criada por execução de build e associa o manifest a cada artefato final.

| Campo | Tipo | Regra |
|---|---|---|
| manifest_sha256 | Sha256 | Digest do manifest normalizado correspondente. |
| build_started_at_utc | timestamp | Registro da execução; não entra na comparação de determinismo do manifest. |
| artifact_name | path relativo | Nome da saída final, nunca path absoluto local. |
| artifact_sha256 | Sha256 | Hash do arquivo efetivamente distribuído. |
| gates | objeto | Estado da aprovação de matriz de arquitetura, licenças e VM limpa: pending, passed ou failed. |
| result | enum | passed, failed ou pending; failed/pending bloqueiam publicação. |

Só se afirma reprodução bit a bit quando os digests dos artefatos são idênticos. Diferença de hash deve ser investigada e explicada mesmo se inputs/manifests forem iguais.

## UserDataRoot

Raiz mantida em local de dados do usuário e definida em F001, independente da pasta onde portable-dir foi extraído ou do diretório escolhido para instalar.

| Grupo | Conteúdo protegido |
|---|---|
| config | Configuração e preferências. |
| data | SQLite, revisões Alembic, backup de upgrade e estado persistido local. |
| logs | Logs rotativos sanitizados, sem credenciais ou conteúdo de livro. |
| cache | Somente conteúdo regenerável marcado como cache. |
| biblioteca/arquivos | Originais, derivados, downloads e exports segundo F006/F008; exports externos não são controlados pelo instalador. |

Instalação, upgrade e desinstalação padrão não reinicializam, reescrevem nem removem essa raiz.

## UpgradeRun e UpgradeBackup

O instalador substitui binários depois do encerramento controlado do aplicativo. A primeira abertura da nova versão coordena migração local; upgrade e migração são fases diferentes.

| Campo | Tipo | Regra |
|---|---|---|
| source_version / target_version | ProductVersion | Release anterior e nova release. |
| source_revision / target_revision | string | Revisão Alembic antes/depois. |
| backup_relative_path | path relativo | Diretório gerenciado de backup em UserDataRoot; nunca pasta arbitrária ou instalação. |
| backup_sha256 | Sha256 | Hash verificado antes de executar migrações. |
| state | enum | requested, backup_created, backup_verified, migrating, succeeded, cancelled_safe, recovery_required. |
| error_code | string | Código tipado estável; mensagem ao usuário em pt-BR e log sem caminhos/segredos sensíveis. |

Fluxo: solicitar encerramento -> aplicativo finaliza jobs e fecha sessão -> criar backup -> validar backup -> aplicar migrações em sequência -> verificar versão/integridade -> habilitar módulos dependentes do banco. Falha mantém backup e a base anterior recuperável. Não executar downgrade automaticamente e não permitir que o instalador reporte sucesso de migração.

Cancelamento ocorre antes de aplicar revisões ou em checkpoint que já concluiu/rollbackou transação; durante operação transacional não interrompe o banco no meio. Se a recuperação exigir restaurar a cópia anterior, explicar origem/destino, criar cópia de segurança do estado falho e solicitar confirmação explícita.

### Migrações

- Alembic registra cada revisão com identificador e vínculo para a revisão anterior; a aplicação sobe até a revisão atual definida pelo projeto.
- Autogeração de diff é somente ponto de partida; cada migration é revisada e tem cenário de upgrade e recuperação.
- Migrações pertencem à infraestrutura de persistência, orquestradas por caso de uso de bootstrap. O domínio não importa SQLAlchemy/Alembic.
- F012 não adiciona tabelas de release ao banco da pessoa usuária. O schema de aplicação e suas migrações iniciais permanecem na F001/F008.
- Instalação limpa, upgrade de fixtures F001–F011, schema futuro desconhecido e arquivo SQLite ausente/corrompido devem produzir estados verificáveis, sem reportar sucesso falso.

## ReleaseChecklistItem

Cada item de release tem id, status (pending, passed, failed), ambiente/par Windows-arquitetura, timestamp, referência de evidência e nota sanitizada. Um item só passa com evidência daquela release. pending é o estado inicial e obrigatório para checks de VM ainda não executados.

## Relações

- Um ReleaseManifest descreve insumos/composição de uma release e referencia vários TargetPairs, PackagedComponents e ArtifactReferences.
- Cada ArtifactAttestation referencia um único manifest e um ou mais artefatos finais identificados por hash.
- Cada ThirdPartyNotice descreve um componente empacotado e aponta para seus textos de licença.
- Uma execução de upgrade possui no máximo um backup validado por revisão de origem; a nova migração só começa depois desse backup.
- Cada ReleaseChecklistItem referencia a versão e o par Windows/arquitetura verificados.
