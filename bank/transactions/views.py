"""
MUDANÇAS:

- Usa o Conservative Two Phase Locking.
- Primeira comunicação é para bloquear todos os bancos de dados. Então Banco A, que está fazendo a requisição, manda um aviso para Banco B e C bloquearem os bancos de dados e espera.
- Se algum banco de dados não for bloqueado, a transação é cancelada.
- Se todos os bancos de dados forem bloqueados, começa a transação do Two phase commit.
- Todos os Bancos precisam se conhecer.
- Um cliente logado em um Banco A consegue fazer transferência de suas contas do Banco B para banco C, do Banco C para o B ou do Banco A para o Banco A.
- Quando um cliente logado estiver fazendo uma transação, todos os outros bancos precisam estar bloqueados de fazer transação nessa conta.
- Esse bloqueio pode acontecer por meio de estados. O banco A se comunica com todos os bancos ao mesmo tempo.
- Se o saldo do cliente A for atualizado no banco A, deve ser enviado uma notificação para todos os bancos atualizarem o valor de A.
- Vai ter de trabalhar bastante com gerenciamento de estados, onde esse estado é compartilhado entre todos os bancos. 

"""
from django.shortcuts import redirect
from accounts.models import Client  # Este cliente do banco
from django.http import JsonResponse
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
from django.contrib import messages
from .models import Bank

def configure():
    # Configurar quem são os bancos conhecidos e se conectar com todos
    # Só irá aparecer para o usuário, os bancos que forem conectados
    # O banco que o cliente está logado será o coordenador.
    pass
    
### Solicita bloqueio de todos os bancos de dados de outros Bancos configurados.
### Colocar em arquivo de scripts.
def lock_all_banks(bank_list, value, client):
    accounts = {}
    for bank in bank_list:
        url = f'http://{bank.ip}:{bank.porta}/lock/'
        try:
            response = requests.post(url, data={'value': value, 'client': client}, timeout=5)
            if response.status_code != 200 or response.json().get('status') != 'LOCKED':
                return False
            accounts[bank.ip] = response.json.get('client_object').blocked_balance #isso pode causar erro
        except (ConnectTimeout, ReadTimeout):
            return False
    return accounts

### Solicita desbloqueio de todos os bancos de dados de outros Bancos configurados.
### Colocar em arquivo de scripts.
def unlock_all_banks(bank_list, client):
    for bank in bank_list:
        url = f'http://{bank.ip}:{bank.porta}/unlock/'
        try:
            response = requests.post(url, data={'client': client}, timeout=5)
        except (ConnectTimeout, ReadTimeout):
            continue

def subtract_balance_all_banks():
    pass

### Requisição recebida por outro Banco para bloquear o banco de dados deste Banco.
### O banco de dados em si não é bloqueado, mas sim o valor na conta do cliente para transação.
### A escolha é bloquear o valor total do saldo do cliente, e não apenas o do valor da transferência.
@csrf_exempt
def lock(request):
    if request.method == "POST":
        client_to_lock = request.POST.get('client')
        value_to_lock = request.POST.get('value')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_lock)
                bank_client.blocked_balance += Decimal(bank_client.balance)
                bank_client.balance = 0
                bank_client.in_transaction = True
                bank_client.save()
                return JsonResponse({'status': 'LOCKED', 'client_object': bank_client}) # tem algum método para fazer to_json?
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

### Requisição recebida por outro Banco para desbloquear o banco de dados deste Banco.
### O banco de dados em si não é debloqueado, mas sim o valor na conta do cliente para transação.
### A escolha é desbloquear o valor total do saldo bloqueado do cliente, e não apenas o do valor da transferência.
@csrf_exempt
def unlock(request):
    if request.method == "POST":
        client_to_unlock = request.POST.get('client')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_unlock)
                bank_client.balance = bank_client.blocked_balance
                bank_client.blocked_balance = Decimal(0)
                bank_client.in_transaction = False
                bank_client.save()
                return JsonResponse({'status': 'UNLOCKED'})
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

### View que coordena transação deste Banco para os outros Bancos.
### Banco para transferir: bank_to_transfer. Bancos para pegar o valor: banks.
### Esta view pega os valores que o cliente deste Banco quer transferir a partir de outros bancos e transfere para o banco que escolher.

"""
Falta passar parâmetro que informa quais bancos e quais valores quer ser retirado desses bancos.
sugestão: banks_and_values_to_steal
"""

def transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer):
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=request.user)

                if bank_client.in_transaction:
                    messages.error(request, "Cliente está em transação no momento. Aguarde.")
                    return redirect('transaction_page')

                if bank_client.balance < value_to_transfer:
                    messages.error(request, "Saldo insuficiente na conta de origem.")
                    return redirect('transaction_page')

                banks = Bank.objects.all()

                ## Inicia transação do Two Phase Locking, bloqueando todas as contas.

                #{ip: saldo_bloqueado}
                balances_from_other_banks = lock_all_banks(banks, value_to_transfer, request.user.username) #accounts[bank.ip] = response.json.get('client_object').blocked_balance
                
                if not balances_from_other_banks:
                    messages.error(request, "Falha ao bloquear todos os bancos para a transação.")
                    unlock_all_banks(banks, bank_client.username)
                    return redirect('transaction_page')
                
                # verifica se o cliente possui saldo nesses outros bancos
                # pega os valores passados por parametro e verifica se é menor ou igual dos balances_from_other_banks

                # precisa pegar os valores desses outros bancos e enviar no primeiro commit: prepare

                ## Inicia transação de dois commits. Primeiro commit: PREPARE.
                # precisa pegar os valores dos outros bancos e enviar esse valor total por aqui
                url_request = f'http://{bank_to_transfer[0]}:{bank_to_transfer[1]}/transaction/receive/'

                response = requests.post(url_request, data={'status': 'INIT', 'value': value_to_transfer, 'client': client_to_transfer}, timeout=5)
                
                if response.status_code != 200 or response.json().get('status') == 'ABORT':
                    # se o banco que ta recebendo abortou, os saldos são desbloqueados sem alteração no valor
                    unlock_all_banks(banks, request.user.username)
                    messages.error(request, f"O Banco {bank_to_transfer} precisou abortar a operação.")
                    return redirect('transaction_page')

                # se o banco que ta recebendo confirmou que o cliente existe, os saldos são subtraidos dos outros bancos 
                # precisa fazer função para subtrair os valores de outros bancos
                # subtrai apenas o valor escolhido pelo cliente deste banco para ser subtraido banks_and_values_to_steal
                if not subtract_balance_all_banks():
                    #se não conseguiu subtrair o valor dos bancos, aborta
                    #verifica se o saldo bloqueado dos outros bancos é igual ao que está em balances_from_other_banks
                    #se for igual, só desbloqueia
                    #se não for igual, ou seja, se já subtraiu, devolve de acordo com balances_from_other_banks
                    pass

                # subtrai inclusive desse banco atual se houver
                bank_client.balance -= value_to_transfer
                bank_client.save()

                ## Segundo commit: COMMIT.
                response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
                
                ## Terceiro commit: ROLLBACK.
                if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                    # se o banco receptor não conseguiu responder, faz o que está em: if not subtract_balance_all_banks():
                    # para devolver os valores 
                    rollback_response = requests.post(url_request, data={'rollback': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
                    if rollback_response.status_code != 200 or rollback_response.json().get('status') != 'ROLLED BACK':
                        raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer} e falha ao reverter a operação.")
                    raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}.")

                # desbloqueia os bancos
                unlock_all_banks(banks, request.user.username)

                messages.success(request, f"Valor de R${value_to_transfer} transferido com sucesso!")

                return redirect('transaction_page')
        except ConnectTimeout:
            messages.error(request, f"ConnectTimeout Error: O host {bank_to_transfer[0]} pode estar inacessível ou indisponível. Pode haver um firewall ou configuração de rede que bloqueei a conexão. O serviço na porta {bank_to_transfer[1]} pode não estar em execução ou não estar respondendo. O tempo limite de conexão pode ser muito curto para a rede ou servidor em questão.")
            return redirect('transaction_page')
        except ReadTimeout:
            messages.error(request, f"A leitura dos dados da resposta da requisição excedeu o tempo limite especificado.")
            return redirect('transaction_page')
        finally:
            unlock_all_banks(banks, request.user.username)

### Cliente só recebe valor se não estiver em transação. Nesta etapa, o valor já está bloqueado.
# valor já está no blocked_balance, precisa mudar a estratégia de 'balance' = blocked_balance e blocked_balance = 'balance_in_transaction'
@csrf_exempt
def receive(request):
    if request.method == "POST":
        client_to_receive = request.POST.get('client')
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'
        rollback = request.POST.get('rollback', 'False') == 'True'

        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_receive)
                
                if commit:
                    bank_client.balance += Decimal(value_to_receive)
                    bank_client.blocked_balance -= Decimal(value_to_receive)
                    bank_client.save()
                    return JsonResponse({'status': 'COMMITTED'})

                if rollback:
                    bank_client.blocked_balance -= Decimal(value_to_receive)
                    bank_client.save()
                    return JsonResponse({'status': 'ROLLED BACK'})

                bank_client.blocked_balance += Decimal(value_to_receive)
                bank_client.save()
                return JsonResponse({'status': 'READY'})
            
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)
