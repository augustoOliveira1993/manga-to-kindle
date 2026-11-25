<!--
Relatório de Impacto da Constituição
- Mudança de versão: modelo inicial → 1.0.0 (primeira constituição do projeto).
- Princípios definidos: os espaços reservados do modelo foram substituídos por cinco princípios.
- Seções adicionadas: Restrições Técnicas e Legais; Fluxo de Desenvolvimento e Critérios de Qualidade.
- Seções removidas: nenhuma; o documento anterior continha apenas espaços reservados do modelo.
- Pendências: nenhuma. A data de ratificação corresponde à criação desta constituição a pedido da pessoa usuária.
-->

# Constituição do Manga to Kindle

## Princípios Fundamentais

### I. Arquitetura Modular e Dependências Explícitas
A aplicação DEVE separar as responsabilidades de domínio, aplicação, infraestrutura e
apresentação. As regras de domínio NÃO DEVEM depender de PySide6, persistência ou serviços
externos. Os casos de uso da aplicação coordenam o trabalho por portas explícitas; os
adaptadores de infraestrutura implementam essas portas; a camada de apresentação em
PySide6 conduz a interação com a pessoa usuária. As dependências DEVEM apontar para dentro,
e as dependências concretas DEVEM ser montadas e injetadas nas fronteiras da aplicação.
As mudanças DEVEM aplicar SOLID para manter responsabilidades claras e componentes
substituíveis.

### II. Simplicidade, Tipagem e Manutenibilidade
O código DEVE usar identificadores claros em inglês e anotações de tipo nas interfaces
públicas e fronteiras de domínio. As implementações DEVEM seguir KISS e YAGNI: abstrações
somente devem ser adicionadas quando houver necessidade demonstrada de fronteira, reúso
ou testabilidade. Ruff e MyPy DEVEM ser usados para análise estática e estilo (lint), além
da verificação de tipos, com configuração explícita e compatível com a versão de Python
suportada.

### III. Operações Responsivas e Canceláveis
Operações de disco, rede, arquivos compactados, imagens e outros I/O ou processamentos
potencialmente demorados NÃO DEVEM bloquear a thread gráfica. Esse trabalho DEVE usar um
mecanismo em segundo plano compatível com o loop de eventos do Qt, informar progresso
quando fizer sentido e permitir cancelamento quando a operação puder ser interrompida com
segurança. A interface DEVE comunicar conclusão, cancelamento e falha sem deixar de
responder.

### IV. Segurança Local dos Dados e Recuperação
Livros e dados da aplicação DEVEM permanecer no dispositivo da pessoa usuária, salvo quando
ela autorizar explicitamente uma transferência específica. Os arquivos de imagem
originais DEVEM ser preservados sem alterações; conversões e processamentos DEVEM gravar em
arquivos separados. Os dados persistidos DEVEM oferecer migrações versionadas. Gravações
com várias etapas DEVEM ser atômicas ou recuperáveis; operações interrompidas DEVEM deixar
estado suficiente para detectar e retomar, repetir ou limpar resultados parciais com
segurança, sem corromper os arquivos de origem.

### V. Funcionalidades Verificáveis e Operações Seguras
Cada funcionalidade DEVE ter critérios de aceitação observáveis, testes automatizados
relevantes e documentação para comportamentos visíveis à pessoa usuária ou fluxos
alterados. As operações DEVEM tratar falhas esperadas em fronteiras claras e apresentar
mensagens acionáveis e sem jargão técnico na interface. Os logs DEVEM ajudar no diagnóstico
sem incluir segredos, credenciais ou conteúdo de livros. Os testes DEVEM usar Pytest e
cobrir o comportamento alterado na camada de unidade, integração ou apresentação
adequada.

## Restrições Técnicas e Legais

- O produto suportado é um aplicativo desktop local para Windows 10 e Windows 11,
  implementado em Python 3.12 ou superior com PySide6.
- `uv` DEVE gerenciar o ambiente e as dependências Python; as aplicações DEVEM registrar
  as versões resolvidas em `uv.lock`. Ruff, MyPy e Pytest DEVEM ser usados para lint,
  verificação de tipos e testes. Versões e APIs de dependências DEVEM ser conferidas na
  documentação oficial e no ambiente resolvido do projeto; contribuidores NÃO DEVEM
  inventar comportamento de APIs ou opções de linha de comando.
- A interface e a documentação voltadas à pessoa usuária DEVEM ser redigidas em português
  brasileiro. O código-fonte, os símbolos e os identificadores DEVEM estar em inglês.
- Uma fonte só DEVE ser usada para download quando autorizar esse uso. A aplicação e suas
  contribuições NÃO DEVEM contornar DRM, CAPTCHAs, autenticação, barreiras de pagamento ou outras
  restrições de acesso. As integrações DEVEM respeitar licenças, termos de uso e limites
  de requisições aplicáveis.
- Baixar ou processar um livro localmente não autoriza seu envio a terceiros. Cada
  transferência DEVE ter autorização explícita da pessoa usuária.
- Logs e diagnósticos DEVEM omitir segredos e conteúdo de livros. A persistência e a
  recuperação locais DEVEM seguir o Princípio IV.

## Fluxo de Desenvolvimento e Critérios de Qualidade

- Antes da implementação, cada funcionalidade DEVE definir critérios de aceitação
  verificáveis e identificar os testes e a documentação necessários para demonstrá-los.
- Uma funcionalidade só está concluída quando seus critérios de aceitação forem atendidos,
  os testes Pytest relevantes forem adicionados ou atualizados e seu comportamento ou
  fluxo de uso estiver documentado.
- Alterações de dependências DEVEM ser resolvidas e registradas com `uv`; a compatibilidade
  declarada DEVE ser sustentada pela documentação das versões escolhidas e pelo ambiente
  do projeto.
- As mudanças DEVEM ser revisadas quanto às fronteiras entre camadas, à responsividade da
  interface, ao cancelamento e progresso quando aplicáveis, à segurança dos dados, ao
  acesso autorizado às fontes e à ausência de segredos nos logs.
- `README.md` e `AGENTS.md` DEVEM permanecer corretos quando houver mudanças de instalação,
  comportamento suportado, comandos de desenvolvimento ou convenções duradouras do
  projeto.

## Governança

Esta constituição rege a especificação, o desenho, a implementação e a revisão das
funcionalidades. A revisão de aceitação de cada funcionalidade DEVE verificar os
princípios e restrições aplicáveis. Toda exceção DEVE registrar motivo, escopo e impacto;
nenhuma exceção DEVE autorizar acesso ilícito, transferência de livros sem autorização ou
perda de imagens originais.

As emendas DEVEM registrar justificativa e impacto. Mudanças que afetem dados persistidos
DEVEM incluir uma abordagem de migração e recuperação. A pessoa mantenedora do projeto
aprova as emendas. O versionamento segue regras semânticas: MAJOR para mudanças
incompatíveis de governança, MINOR para princípios ou seções novos ou materialmente
ampliados e PATCH para esclarecimentos sem mudança de obrigações. A conformidade é
revisada no planejamento e na aceitação das funcionalidades.

**Versão**: 1.0.0 | **Ratificada**: 2026-11-25 | **Última alteração**: 2026-11-25
