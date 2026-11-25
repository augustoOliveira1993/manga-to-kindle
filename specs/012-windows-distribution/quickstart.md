# Quickstart de Validação — F012

## Estado

Este é um roteiro para uso após a implementação de F001–F011 e criação do projeto uv. Não é executável no checkout atual: não há pyproject.toml, uv.lock, código do aplicativo ou arquivo PyInstaller. Nenhum comando abaixo foi executado nesta etapa.

## Pré-requisitos para Build

- Checkout limpo no commit de release.
- Windows nativo na arquitetura aprovada para a matriz de release.
- Versão Python 3.12+ fixada para o pipeline e registrada no manifest.
- uv instalado; pyproject.toml e uv.lock coerentes.
- Grupos de dependência dev (Ruff, MyPy, Pytest) e build (PyInstaller) declarados.
- Chaves/licenças de terceiros não entram no ambiente de build nem em log.
- F001–F011 implementadas, revisadas e com fixtures de teste; licença de todos os pacotes empacotados aprovada.

## Preparar Ambiente e Rodar Checks

Comandos validados na documentação do uv; nomes dos grupos e caminhos são os propostos no plano e só passam a existir após implementação:

    uv sync --locked --group dev --group build
    uv run --locked --group dev pytest
    uv run --locked --group dev ruff check src tests
    uv run --locked --group dev mypy src

Critério: uv falha se pyproject.toml não corresponder ao lock; testes e verificações estáticas concluem antes do empacotamento. Ruff, MyPy e Pytest permanecem fora do artefato de runtime.

## Gerar Bundle Windows

Depois de revisar a spec PyInstaller versionada e o inventário de imports/DLLs:

    uv run --locked --group build pyinstaller packaging/pyinstaller/manga_to_kindle.spec

O caminho posicional de spec file é uma forma documentada de invocar PyInstaller. A configuração executada deve usar os dados contidos na spec; não adicionar flags/hook/import oculto no comando sem confirmar que a versão escolhida os aceita e que a análise do build precisa deles.

Inspecionar o diretório de build e saída. Confirmar PySide6/Qt plugins, runtime, ícone, metadados, migrações, licenças e ausência de ferramentas dev, KCC, navegador e conteúdo de usuário. Nenhuma pasta de config/data/logs/cache do builder pode ser copiada para o produto.

## Manifest, SBOM e Checksums

Validar ReleaseManifest com o schema em contracts/release-manifest.schema.json e cada ArtifactAttestation com contracts/artifact-attestation.schema.json; serialização/validação planejada por Pydantic v2. Gerar e revisar a lista de dependências:

    uv export --locked --format cyclonedx1.5

Registrar os insumos estáveis (commit, lock, versões, spec, imagem do Windows, componentes) no manifest. Para cada saída final, calcular SHA-256 e criar ArtifactAttestation com os gates daquela release. Inventário CycloneDX não substitui THIRD-PARTY-NOTICES nem aprovação manual de licença.

Critérios: hashes têm 64 dígitos hexadecimais; nenhum componente empacotado tem licença desconhecida; architecture_matrix, license_review e clean_vm_validation não podem ficar pending para publicação.

## Testes em VMs Descartáveis

Para cada par Windows/arquitetura aprovado:

1. Criar VM limpa, sem Python, uv, Qt de desenvolvimento, KCC ou browser empacotado.
2. Instalar/extraír artefato e verificar ícone, versão, título, abertura, encerramento e escrita apenas na raiz local de usuário.
3. Com fixtures sintéticas, preencher biblioteca, progresso, preferências, exports e arquivos; registrar IDs, relações e hashes.
4. Atualizar manualmente a partir do build anterior. Simular app aberto, cancelamento, espaço insuficiente, backup inválido e falha de migration. Confirmar backup, integridade e mensagens.
5. Desinstalar pelo fluxo padrão e comparar hashes. Confirmar que dados foram preservados.
6. Reinstalar e confirmar que a biblioteca preservada reabre. Em VM separada, testar opção de remoção de dados com escopo/caminho explícitos e cancelamento.
7. Registrar versão da VM, arquitetura, evidências, resultado e hashes na checklist; deixar “Pendente” tudo que não foi executado.

## Recuperação

- Em migration falha ou versão de banco desconhecida, não continuar a inicialização com serviços que gravam na base.
- Manter backup e estado da tentativa; coletar logs sanitizados e oferecer o procedimento de recuperação definido em F001.
- Se uma restauração for escolhida, salvar uma cópia do estado falho e confirmar o destino antes de substituir a base ativa.
- Nunca usar dados pessoais, livros reais, credenciais ou fontes online nos testes de release.

## Referências

- [Checklist de release](checklists/release.md)
- [Contrato de ciclo do instalador](contracts/installer-lifecycle.md)
- [Manifest de release](contracts/release-manifest.schema.json)
- [Atestação de artefato](contracts/artifact-attestation.schema.json)
- [Modelo de dados](data-model.md)
- [Plano](plan.md)
