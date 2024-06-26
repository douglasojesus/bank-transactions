<div align="center">

# Transações Bancárias Distribuidas 🏦

</div>

# Resumo

<p align="justify">Este relatório aborda a implementação de um sistema distribuido que interconecta aplicações (bancos financeiros) para realizar criação de contas bancárias e gerenciar transações financeiras, semelhante ao modo de transferência do Pix. Os clientes, a partir de qualquer banco, podem realizar transações atômicas sobre o dinheiro em contas de outro banco, inclusive envolvendo mais de duas contas. A comunicação entre os servidores dos bancos deve ser implementada através de um protocolo baseado em uma API REST. Este projeto foi desenvolvido como parte dos estudos da disciplina de Concorrência e Conectividade na Universidade Estadual de Feira de Santana (UEFS).</p>

# Objetivo

<p align="justify">
Desenvolver um sistema de transações bancárias distribuídas que permita a criação de contas bancárias e a realização de pagamentos, depósitos e transferências entre contas de diferentes bancos, em um país sem banco central. O sistema deve garantir a integridade das transações e evitar o duplo gasto.
</p>

# Natureza do Sistema

- Distribuído: O sistema deve operar sem um ponto central de controle, distribuindo as responsabilidades entre os diferentes bancos participantes.
- Atômico: As transações devem ser atômicas, garantindo que todas as operações de uma transação sejam concluídas com sucesso ou nenhuma seja aplicada, mantendo a consistência dos dados.

# Componentes Principais

- Contas Bancárias: O sistema deve suportar a criação e gerenciamento de contas bancárias, incluindo contas físicas, particulares, conjuntas e de pessoas jurídicas.
- Transações: O sistema deve permitir transações como pagamentos, depósitos e transferências, inclusive entre contas de diferentes bancos.

# Comunicação e Integração

- API REST: A comunicação entre os servidores dos bancos deve ser feita através de um protocolo baseado em API REST, facilitando a integração e evitando problemas de bloqueio por firewalls das instituições.
- Contêineres Docker: A solução deve ser desenvolvida utilizando contêineres Docker, permitindo uma fácil implantação e escalabilidade do sistema.
- Frameworks de Terceiros: É permitido o uso de frameworks de terceiros para a implementação das interfaces web e APIs dos servidores, desde que a comunicação interbancária siga o protocolo REST definido.

# Requisitos Funcionais
- Criação de Contas: Permitir a criação de novas contas bancárias de diferentes tipos.
- Realização de Transações: Permitir que os clientes realizem transações financeiras, garantindo a integridade e segurança das mesmas.
- Consistência de Dados: Garantir que as contas não movimentem mais dinheiro do que possuem e evitar o duplo gasto.

# Desafios e Considerações:
- Coordenação Distribuída: Sem um banco central, a coordenação das transações deve ser feita de maneira distribuída, o que exige mecanismos robustos de consenso e coordenação.
- Integridade das Transações: Implementar mecanismos que garantam que uma mesma quantia de dinheiro não seja gasta mais de uma vez (prevenção de duplo gasto).
- Compatibilidade e Interoperabilidade: Garantir que diferentes bancos, possivelmente utilizando sistemas heterogêneos, possam se comunicar e realizar transações de forma eficaz.
- Monitoramento e Manutenção: Implementar sistemas de monitoramento e manutenção para garantir a operação contínua e eficiente do sistema.

# Componentes da Arquitetura:
<p align="center">
  <img src="docs/images/components_architecture.png" alt="Figura 1." width=450>
</p>

# Conexão:
- Cliente (via interface) se comunica com o banco (servidor).
- Banco (através da requisição do cliente) se comunica com outros bancos.
- Banco (através da requisição de outro banco, vinda de outro cliente) gerencia entradas para algum cliente interno.

Exemplo:

Fulano é do banco UEFSBank.
Ciclano é do banco DEXABank.

Fulano decide transferir R$50,00 para Ciclano(DEXABank):

Linha de acontecimentos:

1) Fulano, através da interface web, solicita transferir R$50,00 via requisição web. 
2) UEFSBank recebe, através de sua rota, a requisição de Fulano. Como Fulano tem R$50,00 em sua conta, o valor pode ser transferido. 
3) UEFSBank faz uma requisição para DEXABank para verificar se DEXABank tem Ciclano como cliente.
4) UEFSBank solicita efetuação de transferência para DEXABank.
5) DEXABank responde UEFSBank o status da transferência (se foi feita com sucesso ou não).
6) UEFSBank recebe resposta de UEFSBank e registra saída de valor de Fulano caso recebe o status de feita com sucesso.
7) DEXABank registra entrada de valor de Ciclano.
8) UEFSBank responde interface de Fulano informando o status da transferência. 

Obs: é necessário garantir que as transações sejam atômicas em 4), 5), 6). 7). Questão: quando DEXABank responder (5), como garantir que UEFSBank recebeu a resposta da requisição? Como DEXABank saberá se a resposta chegou corretamente? É necessária outra requisição de confirmação?

# Estratégia de transação atômica:

## Utilizando do Two-phase commit

Para implementar o algoritmo de Two-phase Commit (2PC) com Django para garantir uma transação atômica entre dois bancos, é utilizado o transaction.atomic(). Isso garante que, se houver algum erro, os dados dos bancos não serão alterados.

A primeira função, transfer, é responsável por iniciar a transferência de um valor de um banco para outro. Primeiramente, verifica se o usuário está autenticado. Caso contrário, redireciona para a página de login. Em seguida, utilizando uma transação atômica, obtém os detalhes do cliente do banco atual, garantindo que a linha do cliente esteja bloqueada durante a transação para evitar condições de corrida. Se o saldo do cliente for insuficiente, retorna uma resposta indicando saldo insuficiente. A função então faz uma solicitação POST ao banco destinatário para iniciar a transferência (primeira fase do 2PC). Se o banco destinatário responder com um status de 'ABORT', a operação é cancelada. Caso contrário, o saldo do cliente é debitado e outra solicitação POST é enviada ao banco destinatário para confirmar a transação (segunda fase do 2PC). Se a confirmação falhar, uma exceção é lançada. Se tudo correr bem, a função retorna uma resposta indicando sucesso.

A segunda função, receive, é responsável por lidar com as solicitações recebidas de outros bancos. Ela é decorada com @csrf_exempt para desativar a proteção CSRF para esta visão específica, permitindo que requisições POST sejam aceitas de fontes externas. Quando uma requisição POST é recebida, ela obtém o valor a ser recebido e verifica se é uma solicitação de commit. Utilizando uma transação atômica, tenta obter os detalhes do cliente destinatário, bloqueando a linha do cliente durante a transação. Se o cliente não existir, retorna uma resposta indicando 'ABORT'. Se for uma solicitação de commit, adiciona o valor ao saldo do cliente e retorna uma resposta indicando 'COMMITTED'. Se for uma solicitação de preparação (primeira fase), retorna uma resposta indicando 'READY'. Se a requisição não for um POST, retorna uma mensagem de erro.

Esse código garante que as transferências entre bancos sejam executadas de forma segura e consistente, utilizando o protocolo de commit de duas fases para coordenar a transação entre os bancos e assegurar que ambas as partes concordem em prosseguir antes de qualquer alteração ser confirmada.

Rollback: Introduzi um rollback na função receive que permite reverter a transação caso a confirmação falhe. Se a confirmação falhar, uma solicitação de rollback será enviada ao banco receptor para remover o valor creditado.

Confirmação de Rollback: Se o rollback também falhar, uma exceção será levantada, alertando sobre a falha na confirmação e na reversão, permitindo que um administrador intervenha manualmente para resolver o problema.

A cláusula select_for_update() bloqueia as linhas do banco de dados que são selecionadas até o final da transação. Isso garante que outras transações que tentem acessar essas linhas tenham que esperar até que o bloqueio seja liberado.
Quando um usuário tenta realizar uma transferência, a linha da conta é bloqueada até que a transação seja concluída, evitando que outro usuário faça uma alteração simultânea.

Quando um usuário de uma conta conjunta inicia uma transferência, a linha da conta conjunta é bloqueada. Se outro usuário tentar realizar uma transação enquanto a linha está bloqueada, a transação será colocada em espera até que o bloqueio seja liberado.

Implementando o bloqueio do valor transferido até a confirmação final, podemos evitar inconsistências causadas por transações concorrentes em contas conjuntas. Esta abordagem garante que o valor transferido só estará disponível para uso após a confirmação de que a transação foi concluída com sucesso em ambos os bancos.

# Rotas:

## Admin: usada pelo administrador.
- /admin/

## Auth: usadas pelos clientes.
- /auth/signup/
- /auth/signin/

## Interface: usadas pelos clientes.
- /interface/
- /interface/account/
- /interface/transfer/

## Transactions: usadas pelos clientes e pelos bancos.
- /transaction/transfer/
- /transaction/receive/

## Transações interbancárias: usadas entre os bancos.

### Transferência
1) Autenticação do Usuário: Verifica se o usuário está autenticado. Se não estiver, redireciona para a página de login.
2) Transação Atômica: Inicia uma transação atômica para garantir a consistência dos dados.
3) Captura do Cliente: Obtém o cliente atual do banco e bloqueia a linha correspondente para evitar condições de corrida.
4) Verificação de Saldo: Verifica se o cliente tem saldo suficiente. Se não, retorna um erro.
5) Solicitação de Commit (Primeira Fase): Envia uma solicitação ao banco de destino para iniciar a transação.
6) Processamento do Commit (Segunda Fase): Se a resposta da primeira fase for bem-sucedida, deduz o valor do saldo do cliente e salva.
7) Confirmação do Commit: Envia uma solicitação de commit ao banco de destino. Se a confirmação falhar, tenta reverter a transação.
8) Confirmação da Transação: Após a confirmação bem-sucedida, envia uma solicitação para liberar o saldo bloqueado no banco de destino.

### Recebimento
1) Verificação do Método: Verifica se a requisição é do tipo POST.
2) Captura do Cliente: Obtém o cliente do banco de destino e bloqueia a linha correspondente.
3) Commit: Se a solicitação for de commit, adiciona o valor ao saldo bloqueado e salva.
4) Rollback: Se a solicitação for de rollback, deduz o valor do saldo bloqueado e salva.
5) Confirmação: Se a solicitação for de confirmação, transfere o valor do saldo bloqueado para o saldo disponível e ajusta o saldo bloqueado.
6) Bloqueio de Valor (Primeira Fase): Inicialmente, adiciona o valor ao saldo bloqueado e salva.


# Bibliografia (need organization):

https://docs.djangoproject.com/pt-br/5.0/topics/db/transactions/

