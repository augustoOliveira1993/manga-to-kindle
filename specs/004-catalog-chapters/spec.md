# Especificação de Funcionalidade: F004 — Catálogo e Capítulos do Manga to Kindle

**Feature Branch**: 004-catalog-chapters

**Criado**: 2026-11-25

**Status**: Rascunho

**Entrada**: Integrar a consulta de URL à interface e apresentar metadados opcionais e capítulos com ordenação, identidade e seleção determinísticas. Nenhuma rede real nesta etapa.

## Histórias de Usuário e Testes (obrigatório)

### História 1 — Consultar e reconhecer o catálogo (Prioridade: P1)

Como pessoa usuária, quero informar uma URL na área “Adicionar mangá” e ver o catálogo reconhecido, para confirmar que estou selecionando a obra correta antes de continuar.

**Por que esta prioridade**: A consulta e a apresentação do catálogo são a entrada para a seleção de capítulos e para fluxos posteriores.

**Teste independente**: Consultar a URL sintética documentada pelo provedor de fixtures e conferir os dados fictícios apresentados. Consultar uma URL sem provedor registrado e verificar que ela é recusada sem consulta à rede.

**Cenários de aceitação**:

1. **Dado** que a URL identifica o catálogo sintético do provedor de fixtures, **quando** a pessoa usuária solicita a consulta, **então** o aplicativo apresenta o título e os capítulos determinísticos da fixture e identifica claramente o modo de demonstração.
2. **Dado** que a fixture fornece autor, capa, idioma, volume ou disponibilidade, **quando** o catálogo é exibido, **então** cada valor fornecido aparece associado ao mangá ou capítulo correto.
3. **Dado** que um metadado opcional está ausente, **quando** o catálogo é exibido, **então** o campo fica omitido ou identificado como “Não informado”; nenhum valor é inferido.
4. **Dado** que a URL é inválida, não suportada ou ambígua, **quando** a consulta é iniciada, **então** o fluxo apresenta uma mensagem acionável em português e não apresenta resultados atribuídos a outra fonte.
5. **Dado** que a URL aponta para uma fonte real, **quando** a pessoa usuária tenta consultá-la nesta versão, **então** a aplicação informa que a fonte não está habilitada e não faz conexão de rede.

---

### História 2 — Ordenar e selecionar capítulos (Prioridade: P1)

Como pessoa usuária, quero encontrar capítulos na ordem de leitura e selecionar um capítulo ou intervalo, para escolher com precisão o conteúdo que pretendo processar em uma feature posterior.

**Por que esta prioridade**: Uma lista incorreta ou uma seleção instável pode levar a escolhas diferentes das pretendidas.

**Teste independente**: Usar uma fixture com capítulos numerados, decimais, especiais e números repetidos; comparar a ordem exibida com a regra canônica e conferir a seleção individual e inclusiva por intervalo.

**Cenários de aceitação**:

1. **Dado** capítulos numéricos incluindo 1, 1,5, 2 e 10, **quando** a lista é apresentada, **então** a ordem numérica é crescente e não lexicográfica.
2. **Dado** capítulos especiais sem número, **quando** a lista é apresentada, **então** eles aparecem depois dos numerados, na ordem declarada pela fonte ou, se ausente, em ordem estável por identidade.
3. **Dado** um intervalo definido por dois capítulos visíveis, **quando** a pessoa usuária o seleciona, **então** os dois extremos e todos os itens intermediários na ordem canônica ficam selecionados.
4. **Dado** que os capítulos selecionados continuam presentes após uma atualização, **quando** a lista é atualizada, **então** a seleção dos mesmos IDs estáveis é preservada.
5. **Dado** que IDs distintos têm o mesmo número ou título, **quando** a lista é ordenada, **então** nenhum capítulo é fundido ou ocultado.

---

### História 3 — Atualizar o catálogo e recuperar uma falha (Prioridade: P2)

Como pessoa usuária, quero atualizar os metadados e capítulos e manter o último catálogo válido se a atualização falhar, para não perder meu contexto durante uma indisponibilidade.

**Por que esta prioridade**: O catálogo pode mudar, e uma falha de consulta não deve apagar dados locais úteis nem produzir uma lista parcialmente atualizada.

**Teste independente**: Consultar uma fixture, alterar os dados da fixture e atualizar; em seguida, injetar uma falha tipada de provedor e confirmar que a última versão válida permanece disponível, com indicação do erro e possibilidade de tentar novamente.

**Cenários de aceitação**:

1. **Dado** uma consulta completa e válida, **quando** a pessoa usuária atualiza o catálogo, **então** os registros com IDs estáveis são atualizados em conjunto, os novos IDs são incluídos e a seleção compatível é preservada.
2. **Dado** que a consulta falha ou retorna catálogo inválido, **quando** a atualização termina, **então** nenhum resultado parcial substitui o último catálogo válido e a pessoa usuária pode tentar novamente.
3. **Dado** que uma atualização bem-sucedida não retorna um capítulo anteriormente listado, **quando** a lista atual é aplicada, **então** o item ausente não permanece como capítulo disponível na lista e deixa de fazer parte da seleção.
4. **Dado** uma consulta em andamento, **quando** a pessoa usuária a cancela ou navega para outra área, **então** a interface continua responsiva e o resultado cancelado não é salvo como catálogo completo.

### Casos extremos

- A URL contém espaços externos, fragmento, esquema não permitido, credenciais embutidas ou formato inválido.
- Nenhum provedor, mais de um provedor ou somente provedor de demonstração corresponde à URL.
- A fonte não retorna capítulos, retorna IDs vazios ou duplicados, ou falha ao fornecer título obrigatório.
- Há capítulos com rótulos numéricos inválidos, decimais, especiais, números duplicados ou sem sequência declarada.
- A resposta muda a ordem, o título ou os metadados sem mudar o ID estável; a atualização não duplica o registro.
- Capítulos são adicionados, removidos ou reordenados entre atualizações; IDs não selecionados não são selecionados automaticamente.
- Um metadado opcional ou a capa não existe, está indisponível ou tem referência remota que não pode ser carregada nesta feature.
- O usuário tenta selecionar intervalo invertendo os extremos, intervalo de um único item, intervalo que atravessa capítulos especiais ou intervalo na lista vazia.
- A consulta é cancelada, o provedor falha durante a atualização ou encerra com resposta parcial/inconsistente.
- Um catálogo anteriormente salvo existe, mas a atualização falha; os dados salvos permanecem visíveis e distinguíveis do resultado recém-atualizado.
- Um identificador colide entre provedores ou um mesmo ID é reutilizado indevidamente para conteúdo diferente.

## Requisitos (obrigatório)

### Requisitos Funcionais

- **RF-001**: A área “Adicionar mangá” deve permitir iniciar consulta de catálogo com a URL informada e apresentar os estados vazio, consultando, sucesso, falha e cancelado definidos pela F002.
- **RF-002**: A consulta deve usar a normalização, o registro, a seleção única de provedor e os erros tipados definidos em F003. A URL deve ser validada antes de qualquer operação do provedor.
- **RF-003**: Nesta feature, somente o provedor de fixtures de F003 pode retornar resultados. A interface deve identificar esses resultados como demonstração e não deve atribuir dados fictícios a uma fonte real.
- **RF-004**: A aplicação deve apresentar o título obrigatório do mangá e, quando fornecidos, autor, capa e idioma; deve apresentar título ou número do capítulo e, quando fornecidos, volume e disponibilidade. Campos ausentes devem ser omitidos ou mostrados como “Não informado”, sem inferência.
- **RF-005**: Título de mangá ausente, capítulo sem título e sem número, identidade vazia/duplicada no escopo do provedor ou metadados estruturais inválidos devem tornar o resultado inválido, com erro acionável e sem persistência parcial. A ausência de qualquer metadado opcional não deve invalidar o catálogo.
- **RF-006**: A capa só pode ser exibida a partir de um recurso local fornecido pela fixture nesta etapa. Referências remotas não devem disparar download de imagem; quando não houver capa local disponível, deve ser exibido um espaço reservado neutro, sem imagem inventada.
- **RF-007**: Cada mangá e capítulo deve manter identidade estável e qualificada pelo provedor e pela identidade da fonte. Identificadores não podem depender da posição atual na lista, do título editável ou da ordenação.
- **RF-008**: Capítulos com número explicitamente fornecido e interpretável como valor numérico devem ser ordenados pelo valor numérico crescente, incluindo decimais, sem comparação lexicográfica. O número não deve ser inferido do texto livre do título. Valores numericamente iguais devem manter a sequência da fonte, se declarada; sem sequência, devem usar a identidade estável como desempate.
- **RF-009**: Capítulos especiais ou sem número explícito interpretável devem vir depois dos capítulos numerados. Entre especiais, deve prevalecer a sequência explícita da fonte; se ela não existir, a identidade estável deve definir uma ordem determinística. Títulos e números repetidos não eliminam itens.
- **RF-010**: A pessoa usuária deve poder selecionar e desselecionar capítulos individualmente e selecionar um intervalo inclusivo baseado na ordem exibida. O intervalo deve abranger itens especiais intermediários. Extremos invertidos devem resultar no mesmo intervalo canônico, sem seleção fora dos extremos.
- **RF-011**: A seleção deve ser associada a IDs estáveis. Em uma atualização válida, capítulos com IDs mantidos preservam a seleção; capítulos novos iniciam desmarcados; IDs ausentes deixam de compor a seleção.
- **RF-012**: A aplicação deve permitir atualização explícita do catálogo. Uma resposta completa e válida deve substituir atomicamente a versão visível e persistida, sem duplicar registros com IDs existentes.
- **RF-013**: Falha de rede simulada, indisponibilidade, cancelamento, resposta parcial ou erro de validação deve preservar integralmente o último catálogo válido. A tela deve indicar que os dados são anteriores, apresentar a causa sem detalhes sensíveis e oferecer nova tentativa quando aplicável.
- **RF-014**: Uma falha de provedor deve ser mapeada do erro tipado de F003 para uma mensagem útil em português brasileiro; URL completa, parâmetros sensíveis, credenciais, respostas e conteúdo de livros não podem aparecer em logs ou mensagens.
- **RF-015**: A consulta e a atualização não podem bloquear a thread gráfica. Quando a operação puder ser interrompida com segurança, devem permitir cancelamento; progresso deve ser informado quando a duração justificar.
- **RF-016**: Metadados opcionais novos devem ser persistidos localmente de modo compatível com o contrato de F001 e com migração versionada. Em dados existentes, esses campos começam ausentes; a migração não deve inventar metadados nem alterar imagens originais.
- **RF-017**: A gravação de uma atualização deve ser atômica ou recuperável. Interrupção ou falha não pode deixar o banco com mistura parcial do catálogo antigo e novo.
- **RF-018**: Testes automatizados devem cobrir consulta por fixture, campos opcionais ausentes, ordem numérica e especial, desempate, seleção individual e por intervalo, IDs estáveis, atualização válida, preservação após falha/cancelamento e ausência de tráfego de rede.
- **RF-019**: A documentação do usuário deve explicar consulta, atualização, modo de demonstração, ordenação, seleção por intervalo e limitações de fontes reais. O README deve permanecer consistente com o estado suportado do aplicativo.
- **RF-020**: Nenhuma operação desta feature pode baixar capítulos, modificar páginas/imagens, converter ou enviar livros a um dispositivo.

### Requisitos Não Funcionais

- **RNF-001**: Interface e documentação voltadas à pessoa usuária devem estar em português brasileiro; símbolos e identificadores do código permanecem em inglês.
- **RNF-002**: A navegação, foco, atualização da seleção e cancelamento devem permanecer responsivos em até 200 ms enquanto uma consulta estiver em andamento, conforme o perfil de referência definido em F002.
- **RNF-003**: Os mesmos dados e a mesma ordem declarada pela fixture devem produzir a mesma lista, os mesmos IDs e a mesma seleção em todas as execuções.
- **RNF-004**: A seleção por teclado deve ser possível e perceptível nos temas claro e escuro; estado não deve ser comunicado somente por cor.
- **RNF-005**: Os dados do catálogo e as preferências permanecem no dispositivo local. Logs não contêm URLs completas com parâmetros, credenciais, conteúdo de livros ou segredos.
- **RNF-006**: A aplicação deve falhar de forma segura diante de erro de validação, ambiguidade, destino recusado ou resposta inconsistente, sem tentar outra fonte implicitamente.
- **RNF-007**: Não pode ocorrer acesso à rede durante os cenários F004. Falhas de rede e respostas externas são simuladas por fixtures/falsos de teste até que a autorização de uma fonte real seja verificada separadamente.

### Entidades Principais

- **Manga**: Entidade de F001 com ID e título obrigatórios e referência à fonte; autor, capa e idioma são metadados opcionais.
- **Chapter**: Entidade de F001 associada a um mangá, com ID estável e título ou número que permita leitura inequívoca; volume e disponibilidade são opcionais. A posição de leitura deve ser derivável de número, sequência declarada e regra de desempate.
- **Metadados de catálogo**: Valores efetivamente fornecidos pelo provedor. Ausência representa desconhecido, não um valor inferido.
- **Seleção de capítulos**: Conjunto de IDs estáveis e, durante a interação, intervalo inclusivo calculado sobre a ordem canônica exibida.
- **Resultado de atualização**: Catálogo completo validado que pode substituir a versão local; uma falha não é resultado persistível.

## Critérios de Sucesso (obrigatório)

### Resultados Mensuráveis

- **CS-001**: Em 10 consultas consecutivas à mesma URL sintética, 10 de 10 resultados apresentam os mesmos metadados, IDs e capítulos ordenados, sem duplicação e sem chamadas de rede.
- **CS-002**: Em todos os casos de teste com capítulos 1, 1,5, 2 e 10, a ordem exibida é crescente numericamente; todos os casos de especiais e números repetidos seguem a regra de ordenação definida.
- **CS-003**: Em 100% dos casos de metadados opcionais ausentes, nenhum valor factual é inventado; campos estruturais obrigatórios ausentes produzem erro sem persistência parcial.
- **CS-004**: Em 100% dos casos de seleção por intervalo, os extremos e os itens intermediários da ordem canônica — inclusive especiais — são selecionados, e nenhum item externo é selecionado.
- **CS-005**: Em 100% dos casos de atualização com falha, cancelamento ou resposta inválida, o último catálogo válido permanece íntegro e selecionável.
- **CS-006**: A navegação, seleção e cancelamento respondem em até 200 ms no perfil de referência de F002 enquanto a consulta está ativa.
- **CS-007**: Todos os fluxos de F004 são concluídos sem requisição de rede, download de imagem ou capítulo, alteração de imagens originais, conversão ou transferência.

## Premissas

- A especificação da F003 define que o único provedor disponível até autorização verificável de uma fonte real é o provedor de fixtures, que opera sem rede.
- A fixture fornecerá casos determinísticos de metadados completos e incompletos, capítulos numéricos/decimais/especiais, IDs estáveis, atualização e falha tipada.
- O título do mangá e a identidade/associação do capítulo são dados estruturais; autor, capa, idioma, volume e disponibilidade podem estar ausentes.
- A ordenação numérica usa somente o número fornecido como metadado, sem tentar extraí-lo do título. Se a fonte não declarar ordem para itens empatados ou especiais, a identidade estável será o desempate determinístico. Especiais ficam após os capítulos numerados.
- A seleção por intervalo usa a ordem canônica visível e inclui todos os itens entre os extremos, ainda que a pessoa usuária indique primeiro o extremo posterior.
- “Não informado” e o espaço reservado neutro são estados de apresentação, não metadados persistidos.
- O catálogo salvo localmente é substituído somente após resposta completa e validação bem-sucedida.
- A consulta não cria Page local a partir de referência remota de página da F003. O fluxo real de páginas e imagens depende de feature posterior autorizada.
- O arquivo docs/roadmap.md não foi encontrado no repositório durante esta especificação. A posição F004 decorre da sequência F001–F003 e deve ser conferida quando o roadmap estiver disponível.

## Dependências, Riscos e Limites de Escopo

### Dependências

- Constituição do projeto em [../../.specify/memory/constitution.md](../../.specify/memory/constitution.md), especialmente arquitetura por camadas, responsividade, persistência local, migrações, operações atômicas, autorização e testes.
- F001 — [Fundação do Manga to Kindle](../001-app-foundation/spec.md): contratos Manga/Chapter, SQLite, migrações versionadas, configuração, logs e ciclo de vida local.
- F002 — [Interface desktop do Manga to Kindle](../002-desktop-interface/spec.md): tela Adicionar mangá, URL, estados, seleção múltipla, teclado e limite de responsividade.
- F003 — [Provedores extensíveis do Manga to Kindle](../003-extensible-providers/spec.md): normalização/validação de URL, registro e capacidades dos provedores, erros tipados e fixture determinística.
- Não foi encontrado docs/roadmap.md. Nenhuma dependência de F005–F012 é presumida.

### Bloqueio de Fonte Real

- **B003-REAL-SOURCE** continua vigente: F003 não aprovou uma fonte com autorização verificável para baixar o conteúdo pretendido para uso local. F004 deve funcionar integralmente com fixtures e não remove esse bloqueio. Uma futura integração real exige nova verificação de autorização, documentação, limites, atribuição e obrigações de retirada antes de qualquer acesso.

### Riscos e Mitigações

| Risco | Mitigação exigida |
|---|---|
| Comparação lexicográfica ordena 10 antes de 2. | Definir e testar uma chave numérica canônica, com casos decimais. |
| Mudança de posição altera identidade ou seleção. | Usar IDs estáveis qualificados pela fonte; nunca usar índice como identidade. |
| Metadado ausente é preenchido por inferência. | Tratar optionalidade explicitamente e testar ausência; não transformar desconhecido em “disponível” ou outro valor factual. |
| Atualização parcial corrompe catálogo ou seleção. | Validar o resultado completo e aplicar a persistência atomicamente; preservar última versão em falhas. |
| Uma capa remota provoca acesso não autorizado ou inseguro. | Nesta feature, exibir somente recurso local da fixture e não buscar referências remotas. |
| Mensagens/logs expõem parâmetros da URL ou conteúdo. | Usar erros tipados com mensagens sanitizadas e omitir URL completa e conteúdo. |
| Dados da fixture parecem vir de uma fonte real. | Marcar demonstração de forma visível e recusar URLs reais não suportadas sem rede. |

### Fora do Escopo

- Qualquer provedor real, scraping ou conexão com fontes remotas; remoção do bloqueio B003-REAL-SOURCE.
- Download de capítulos, páginas ou capas remotas, armazenamento de bytes, cache de imagens ou criação de Page local.
- Conversão para formato Kindle, envio por USB, e-mail, nuvem ou qualquer transferência.
- Login, armazenamento de credenciais, CAPTCHA, contorno de DRM, paywall ou outras restrições.
- Edição manual de metadados e gerenciamento geral de biblioteca além de consultar, atualizar e selecionar o catálogo.
- APIs, opções de linha de comando, esquemas de rede ou decisões internas de implementação não validadas.

### Estratégia de Verificação

A feature deve incluir testes automatizados de domínio para ordenação, desempate e intervalo; testes do fluxo com provedor de fixture e falhas simuladas; testes da apresentação para estados, metadados opcionais, teclado e responsividade; e teste de integração da persistência/migração e substituição atômica. Todos os testes devem substituir o transporte externo e afirmar que nenhuma chamada de rede real ocorre. A documentação deve permitir reproduzir manualmente a consulta sintética e identificar o estado de demonstração.
