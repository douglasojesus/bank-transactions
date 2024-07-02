# Bank Transactions System

Este é um sistema para processamento de transações bancárias, utilizando Docker e Docker Compose para configurar e executar três aplicações separadas.

# Resumo

<p>Este relatório aborda a implementação de um sistema bancário distribuído utilizando o framework Django e o banco de dados PostgreSQL. São executados 3 servidores fixos no docker-compose. O servidor disponibiliza rotas para interface gráfica e para comunicação entre outros servidores. Com a interface gráfica, o usuário consegue efetuar configurações, manipulação de contas e realização de transferências. A comunicação entre servidores acontece para realizar transferência de valores de algum dos bancos do consórcio da conta de um usuário para algum outro banco. Este projeto foi desenvolvido como parte dos estudos da disciplina de Concorrência e Conectividade na Universidade Estadual de Feira de Santana (UEFS).</p>

# Sumário

# Gerenciamento de Contas

## O sistema realiza o gerenciamento de contas? Criar e realizar transações?

<p>Para o gerenciamento de contas, o sistema utiliza um modelo de usuário personalizado denominado Client, que herda de AbstractBaseUser e PermissionsMixin do Django. Este modelo contém campos essenciais como nome, sobrenome, email, nome de usuário, saldo (balance), saldo bloqueado (blocked_balance), e status de transação. A criação de novos usuários é gerenciada pelo ClientManager, uma classe personalizada que facilita a criação e configuração de novos objetos de usuário. Este gerenciador assegura que todos os usuários tenham um email único e uma senha segura.</p>

<p>A autenticação dos usuários é realizada por meio de views dedicadas, como sign_in_page para login, logout_page para logout, e sign_up_page para registro de novos usuários. Durante o processo de login, o sistema valida as credenciais fornecidas pelo usuário e, em caso de sucesso, autentica o usuário e o redireciona para a página de sua conta. Para registro, o sistema coleta as informações necessárias através de um formulário, cria uma nova instância de Client, e a salva no banco de dados.</p>

<p>A realização de transações é uma das funcionalidades centrais do sistema e é gerenciada por uma combinação de views, formulários e comunicação entre servidores. A view transaction_page é responsável por gerenciar a lógica das transações, permitindo que os usuários realizem transferências, depósitos e pagamentos. Esta view utiliza um formulário (TransactionForm) para capturar os dados da transação, como o valor a ser transferido, o banco destinatário, e o cliente destinatário. Com base na ação selecionada pelo usuário (transferência, depósito ou pagamento), a view executa a lógica apropriada para atualizar os saldos das contas envolvidas.</p>

<p>Para facilitar a transferência de valores entre diferentes bancos, o sistema utiliza uma função chamada external_client_info, que realiza requisições HTTP para outros servidores bancários, obtendo informações sobre o saldo dos clientes. Esta comunicação entre servidores é essencial para garantir que as transferências interbancárias sejam realizadas de forma eficiente e segura. A view transaction_page também manipula a lógica de retirada de valores de múltiplos bancos, processando uma string de entrada que especifica os valores a serem retirados de cada banco participante.</p>

<p>Além das operações de transferência, o sistema permite que os usuários realizem depósitos e saques diretamente através da interface gráfica. Para depósitos, o saldo do usuário é incrementado pelo valor especificado, enquanto para saques, o saldo é decrementado. Estas operações são feitas apenas no banco coordenador. Então o usuário "Fulano" só poderá depositar e sacar valores no banco em que ele está manipulando. A comunicação atômica com outros servidores só acontece na transação de transferência, que pode ocorrer através de "n" bancos para algum outro banco.</p>









# Realização de Transferência Entre Diferentes Contas

# Comunicação Entre Servidores

# Sincronização em um Único Servidor

# Algoritmo da Concorrência Distribuída

## Empregação

## Funcionamento

# Tratamento da Confiabilidade

# Transação Concorrente

# Conclusão

# Configuração Inicial do Uso do Docker

## Clonando o Repositório

```bash
git clone https://github.com/douglasojesus/bank-transactions.git
cd bank-transactions/
```

## Construindo os contêineres:
```bash
docker-compose build
```

## Executando o sistema:
```bash
docker-compose -p projeto up
```
Isso iniciará todos os contêineres necessários para os aplicativos.

## Configuração dos Bancos de Dados

Para configurar os bancos de dados, você precisará dos IPs dos contêineres. Você pode encontrá-los usando o comando `docker ps` e, em seguida, inspecionando cada contêiner conforme mostrado abaixo:

## Obtenção dos IPs dos Contêineres

```bash
sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bank-transactions-app1-1
sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bank-transactions-app2-1
sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' bank-transactions-app3-1
```

## Acesso aos Servidores
Acesse cada servidor utilizando o IP correspondente para configurar os bancos de dados conforme necessário.

## Testes Automatizados
Você pode usar o arquivo teste_automatizado/main.py para automatizar o acesso às URLs dos contêineres e testar o sistema.
```bash
cd teste_automatizado/main.py
sudo python3 main.py
```

Conservative Two-Phase Locking (C2PL)

O Conservative Two-Phase Locking é um protocolo de controle de concorrência que requer que uma transação adquira todos os bloqueios necessários antes de iniciar sua execução. Ele difere do Two-Phase Locking (2PL) no sentido de que todos os bloqueios são obtidos antes de qualquer operação de leitura ou escrita ocorrer.

Fase de Bloqueio Completo: Antes de iniciar a execução, a transação adquire todos os bloqueios necessários. Nenhum item é bloqueado até que todos os itens estejam prontos para serem bloqueados, evitando assim que um item não bloqueável cause a espera (Hold and Wait).

Eliminação de Deadlock: Se um item não estiver disponível para bloqueio, todos os bloqueios são liberados e a transação tenta novamente mais tarde, sem manter bloqueios enquanto espera.

Two-Phase Locking (2PL)
O Two-Phase Locking é um protocolo de controle de concorrência amplamente utilizado em produtos de banco de dados comerciais. Ele divide a execução de uma transação em duas fases distintas:

Fase de Crescimento (Growing Phase): Durante esta fase, a transação adquire sequencialmente todos os bloqueios necessários para os itens de dados que irá acessar. Nenhum bloqueio é liberado durante esta fase.

Fase de Redução (Shrinking Phase): Inicia-se quando o primeiro bloqueio é liberado. Nesta fase, a transação começa a liberar os bloqueios, um após o outro, e não adquire nenhum novo bloqueio.

Propriedade Adicional: Todas as histórias que resultam do uso do 2PL têm a propriedade adicional de que as operações de bloqueio são ordenadas para cumprir a separação em duas fases.

Para mais detalhes sobre o Two-Phase Locking, consulte este documento.

Essas estratégias são essenciais para garantir a consistência e a integridade dos dados em ambientes de banco de dados multiusuário, prevenindo impasses (deadlocks) e conflitos de acesso simultâneo aos dados.

Bibliografia:
https://www.imperial.ac.uk/media/imperial-college/faculty-of-engineering/computing/public/1617-ug-projects/David-Pollak---Reasoning-about-Two-phase-Locking-Concurrency-Control.pdf
https://www.naukri.com/code360/library/conservative-2-phase-locking

## Gerenciamento do saldo:

São usados dois algoritmos: o two-phase commit e o two-phase locking. Cada um tem 2 fases.

### 1° Fase - Two Phase Locking:

Saldo -> Saldo Bloqueado

### 2° Fase - Two Phase Locking:

### 1° Fase - Two Phase Commit:

Saldo Bloqueado -> Em Transação

### 2° Fase - Two Phase Commit:

Em Transação -> Saldo Bloqueado

### 3° Fase - Two Phase Commit:

### 2° Fase - Two Phase Locking:

Saldo Bloqueado -> Saldo
