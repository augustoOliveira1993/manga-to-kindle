# Contrato de Instalação, Atualização e Remoção

## Princípios

- A UI do instalador e as mensagens do aplicativo relacionadas ao ciclo de release são em português brasileiro, navegáveis por teclado e legíveis por leitor de tela.
- Bundle portátil e diretório de instalação são distintos da raiz de dados local criada por F001/F008.
- Instalação, atualização e remoção não solicitam nem usam credenciais Amazon, SMTP ou de provedores.
- Não há download/atualização automática, telemetria ou chamadas de rede no primeiro início.
- O estado inicial de qualquer operação que ainda não tenha evidência é Pendente.

## Instalação

1. O pacote portátil extrai apenas arquivos do produto; a opção Inno, se aprovada, instala por usuário como caminho padrão e não exige elevação para gravar dados.
2. A pessoa usuária escolhe o diretório do aplicativo. O instalador apresenta que banco, biblioteca, logs, configurações e cache ficam na raiz local de usuário, independentemente desse diretório.
3. A instalação não cria, limpa nem migra a biblioteca. O aplicativo não é iniciado automaticamente sem escolha da pessoa usuária.
4. Na primeira inicialização, o aplicativo abre a janela e completa bootstrap/migração local conforme F001; erro é exibido em pt-BR e logado sem segredos/conteúdo.

## Atualização Manual

1. A pessoa usuária inicia a atualização a partir de um pacote escolhido manualmente. Não há updater, busca de versão ou download silencioso.
2. Se o aplicativo estiver aberto, a operação pede que a pessoa salve/encerre. Jobs recebem encerramento cooperativo. O instalador nunca termina o processo à força nem altera banco em uso.
3. Se não for possível encerrar com segurança, a atualização é cancelada sem mudar binários ou dados.
4. A troca de binários não executa SQL nem altera a raiz de dados. Se a substituição falhar, a operação informa quais arquivos foram atualizados e mantém procedimento/cópia recuperável do aplicativo anterior conforme a capacidade suportada pelo pacote.
5. Na próxima abertura da nova versão, a camada de aplicação cria e valida backup antes de executar Alembic. A UI permanece responsiva; sinais Qt comunicam progresso, sucesso, cancelamento seguro ou erro. Recursos que dependem do schema ficam indisponíveis até a migração terminar.
6. Se a migração falhar, não reporta sucesso, não apaga o backup, não prossegue com gravações incompatíveis e apresenta opção/procedimento de recuperação. Nenhuma restauração sobrescreve a única cópia válida sem confirmação.

## Cancelamento e Falhas

- Antes de iniciar substituição de arquivos ou migration, Cancelar preserva o estado anterior.
- Durante uma etapa atômica/transacional, cancelar solicita parada cooperativa no próximo checkpoint seguro; não interrompe uma transação SQLite no meio.
- Disco cheio, arquivo em uso, versão de origem desconhecida, backup inválido e falha de acesso têm mensagem acionável, estado final explícito e log sanitizado.
- Uma operação parcialmente concluída nunca aparece como concluída. A pessoa usuária recebe resumo do que ficou instalado/preservado e o procedimento para retomar ou recuperar.

## Desinstalação

1. A opção padrão remove apenas arquivos do produto, atalhos e registros de instalação; a raiz de dados e seus arquivos são preservados.
2. Remoção de dados é uma opção separada, desmarcada por padrão. Antes de confirmar, mostrar caminho resolvido e categorias que serão removidas.
3. Exports externos, pastas/fontes de importação, originais externos e qualquer caminho fora do escopo explicitamente confirmado ficam preservados.
4. A confirmação destrutiva descreve os dados exatos e exige ação positiva separada da confirmação comum de desinstalação.
5. Cancelar a desinstalação ou remoção mantém os dados esperados. Se uma limpeza confirmada falhar, reportar remoção parcial e caminho restante; nunca afirmar que os arquivos foram eliminados.

## Contrato de Persistência e Compatibilidade

- Aplicativo instalado pode reconhecer somente revisões Alembic compatíveis declaradas pelo build atual.
- Revisão de banco mais nova que a aplicação é incompatibilidade explícita; não executar downgrade nem apagar base.
- Antes/depois de upgrade, testes usam IDs/relacionamentos sintéticos e SHA-256 de arquivos. A versão da aplicação, migração e backup são registrados localmente sem conteúdo do livro.
- O instalador não define o schema da aplicação. A composição de domínios, casos de uso, adapters SQLAlchemy/Alembic e UI Qt é descrita no plano; não há endpoint público nem CLI de produto criada por este contrato.

## Relação com Critérios da Spec

Este contrato detalha RF-012 a RF-019, RF-025 a RF-028 e CS-002 a CS-004/CS-008/CS-009. A validação só é aprovada com evidência na checklist de release para cada par Windows/arquitetura declarado.
