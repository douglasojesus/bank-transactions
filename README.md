Conservative Two-Phase Locking: este protocolo obriga a transação a bloquear todos os itens que acessa antes de iniciar a execução. Nenhum dos itens será bloqueado pela transação se algum objeto pré-declarado não puder ser bloqueado. Em vez disso, ele espera até que todos os itens estejam prontos para serem bloqueados antes de prosseguir.

Este protocolo não possui fase de crescimento, pois é necessário bloquear os dados antes de utilizá-los. Além disso, esta regra elimina o deadlock liberando todos os bloqueios e tentando novamente mais tarde se um item não estiver acessível para bloqueio, ou seja, sem Hold and Wait.

Como o 2PL garante que nenhum impasse ocorra?
O protocolo emprega bloqueios aplicados aos dados por uma transação e pode impedir que outras transações acessem os mesmos dados durante toda a vida da transação.
Os bloqueios são aplicados e retirados em duas etapas de acordo com o protocolo 2PL:
1) Os bloqueios são obtidos e nenhum bloqueio é liberado durante a fase de expansão.
2) Os bloqueios são liberados e nenhum bloqueio é adquirido durante a etapa de redução.

Ref: https://www.naukri.com/code360/library/conservative-2-phase-locking

Two-Phase-Locking (2pl) is a concurrency control protocol which is vastly used in commercial DBS products. In its base version, as the name suggests, each transaction Ti
’s execution
can be divided into two phases [3]: a growing phase where Ti sequentially acquires locks for all
the data items it is going to access, and a shrinking phase that starts on the first lock release
and will unlock all the items it holds, one after the other. According to 2pl, during the growing
phase no locks are released, and once the shrinking phase has started, no locks are acquired.
Formally, all histories that result from the use of 2pl will have an additional property in comparison to the ones already mentioned for locking protocols. In fact lock operations will be
further ordered as to comply with the two phase separation:
∀x, y, κa, κb, i.({L[κa, x]i
,U[κb, y]i} ⊂ ΘH =⇒ L[κa, x]i @˙ U[κb, y]i)
A variation of the method is Conservative Two-Phase-Locking (c2pl) that works in a similar
way with the key difference that all locks ever needed as part of a transaction are acquired
before any read or write operation happens. As a consequence, we can state that all histories
H adhering to c2pl will be such that:
∀x, op, κ, i.(op 6= L ∧ {L[κ, x]i
, op} ⊆ ΘH) ⇒ L[κ, x]i @˙ op
This is done primarily in order to prevent situations in which 2pl would exhibit deadlocks,
since lock acquisitions can be done in some precise order that all transactions need to follow.

https://www.imperial.ac.uk/media/imperial-college/faculty-of-engineering/computing/public/1617-ug-projects/David-Pollak---Reasoning-about-Two-phase-Locking-Concurrency-Control.pdf

Para rodar o Sistema:

git clone https://github.com/douglasojesus/bank-transactions.git
cd bank-transactions/bank/
docker-compose build
docker-compose up

para ver o banco de dados:
abre o pgAdmin


docker build -t bank .
docker run --network='host' -it --name container_bank bank

remover todas imagens:
docker rmi $(docker images -a -q)

instalar o docker compose:
sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
