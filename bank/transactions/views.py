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
from django.shortcuts import redirect, render
from accounts.models import Client  # Este cliente do banco
from django.http import JsonResponse
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
from django.contrib import messages
from .models import Bank
import logging

logging.basicConfig(level=logging.DEBUG)  # Configura o nível de log para DEBUG

CONFIGURED = False

@csrf_exempt
def configure(request):
    global CONFIGURED
    print(CONFIGURED)
    if not CONFIGURED:
        if request.method == 'POST':
            names = request.POST.getlist('name[]')
            ips = request.POST.getlist('ip[]')
            portas = request.POST.getlist('port[]')

            print(names, ips, portas)

            for name, ip, porta in zip(names, ips, portas):
                print("entrei no for")
                bank = Bank.objects.create(name=name, ip=ip, port=porta)
                bank.save()
                print("salvei um banco")
                
            print("salvei todos os bancos")

            CONFIGURED = True
            messages.success(request, "Bancos adicionados ao consórcio. Garanta que nos outros bancos, esses bancos também tenham sido registrados.")
            # talvez fazer requisição para esses bancos para eles salvarem esse banco tbm
            return redirect('home_page')
    else:
        messages.error(request, "Os bancos já foram adicionados ao consórcio uma vez.")
        
    banks = Bank.objects.all()
    return render(request, 'configure.html', {'banks': banks})

def verify_balance(request, username):
    cliente = Client.objects.get(username=username)
    return JsonResponse({'balance': cliente.balance}, status=200)

### Solicita bloqueio de todos os bancos de dados de outros Bancos configurados.
### Colocar em arquivo de scripts.
def lock_all_banks(bank_list, value, client, ip_bank_to_transfer):
    client.blocked_balance += Decimal(client.balance)
    client.balance = 0
    client.in_transaction = True
    client.save()
    accounts = {}
    for bank in bank_list:
        if bank.ip != ip_bank_to_transfer: # Só bloqueia os bancos que vão enviar dinheiro. 
            url = f'http://{bank.ip}:{bank.port}/transaction/lock/'
            try:
                response = requests.post(url, data={'value': value, 'client': client.username}, timeout=5)
                if response.status_code != 200 or response.json().get('status') != 'LOCKED':
                    print("nao estava locked o retorno para bloquear todos os bancos")
                    return False
                accounts[bank.name] = response.json().get('blocked_balance') 
            except (ConnectTimeout, ReadTimeout):
                print("deu excecao al bloquear todos os bancos")
                return False
        else:
            url = f'http://{bank.ip}:{bank.port}/transaction/verify_balance/{client.username}/'
            response = requests.get(url)
            accounts[bank.name] = response.json().get('balance') 

    return accounts

### Solicita desbloqueio de todos os bancos de dados de outros Bancos configurados.
### Colocar em arquivo de scripts.
def unlock_all_banks(bank_list, client, ip_bank_to_transfer):
    client.balance = client.blocked_balance
    client.blocked_balance = Decimal(0)
    client.in_transaction = False
    client.save()
    for bank in bank_list:
        url = f'http://{bank.ip}:{bank.port}/transaction/unlock/'
        if bank.ip != ip_bank_to_transfer: # Só desbloqueia bancos que enviam
            try:
                response = requests.post(url, data={'client': client.username}, timeout=5)
            except (ConnectTimeout, ReadTimeout):
                continue

# Solicita subtração dos valores dos bancos que efetuarão a transferência.
def subtract_balance_all_banks(bank_client, bank_list, banks_and_values_withdraw):
    for key, value in banks_and_values_withdraw.items():
        if key == 'this':
            # subtrai inclusive desse banco atual se houver
            bank_client.blocked_balance -= Decimal(value)
            bank_client.save()
        else:
            for bank in bank_list:
                if bank.name == key:
                    bank_obj = bank
                    break
            url = f'http://{bank_obj.ip}:{bank_obj.port}/transaction/subtract/'
            response = requests.post(url, data={'client': bank_client.username, 'value': value}, timeout=5)
            logging.debug(f"response: {response}")
            if response.json().get('status') == 'ABORT':
                return False
    return True
    
# Subtrai do valor bloqueado o valor a ser transferido deste banco.
@csrf_exempt
def subtract(request):
    if request.method == 'POST':
        client_to_subtract = request.POST.get('client')
        value_to_subtract = request.POST.get('value')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_subtract)
                bank_client.blocked_balance -= Decimal(value_to_subtract)
                bank_client.save()
                return JsonResponse({'status': 'COMMITED'})
        except:
            return JsonResponse({'status': 'ABORT'}, status=404)
    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

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
                if bank_client.in_transaction:
                    return JsonResponse({'status': 'ABORT', 'message': 'IN_TRANSACTION'}, status=404)
                bank_client.blocked_balance += Decimal(bank_client.balance)
                bank_client.balance = 0
                bank_client.in_transaction = True
                bank_client.save()
                return JsonResponse({'status': 'LOCKED', 'client': bank_client.username, 'blocked_balance': bank_client.blocked_balance}) # tem algum método para fazer to_json?
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

@csrf_exempt
def get_user_info(request):
    username = request.POST.get('username')
    client = Client.objects.filter(username=username).first()
    if client:
        return JsonResponse({'balance': client.balance}, status=200)
    else:
        return JsonResponse({'error': 'Client not found'}, status=404)

def verify_balance_otherbanks(banks_and_values_withdraw, balances_from_other_banks):
    for key, value in banks_and_values_withdraw.items():
        if key != 'this':
            if (Decimal(value) > Decimal(balances_from_other_banks[key])):
                return False
    return True

def return_to_initial_balances(bank_client, bank_list, banks_and_values_withdraw):
    for key, value in banks_and_values_withdraw.items():
        if key == 'this':
            bank_client.blocked_balance = Decimal(value)
            bank_client.save()
        for bank in bank_list:
            if bank.name == key:
                bank_obj = bank
                break
        url = f'http://{bank_obj.ip}:{bank_obj.port}/transaction/return_to_initial_balance/'
        response = requests.post(url, data={'client': bank_client.username, 'value': value}, timeout=5)
        if response.json().get('status') == 'ABORT':
            return False, bank_obj
    return True, bank_obj

@csrf_exempt
def return_to_initial_balance(request):
    if request.method == 'POST':
        client_to_return = request.POST.get('client')
        value_to_return = request.POST.get('value')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_return)
                bank_client.blocked_balance = Decimal(value_to_return)
                bank_client.save()
                return JsonResponse({'status': 'COMMITED'})
        except:
            return JsonResponse({'status': 'ABORT'}, status=404)
    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

### View que coordena transação deste Banco para os outros Bancos.
### Banco para transferir: bank_to_transfer. Bancos para pegar o valor: banks.
### Esta view pega os valores que o cliente deste Banco quer transferir a partir de outros bancos e transfere para o banco que escolher.

"""
Falta passar parâmetro que informa quais bancos e quais valores quer ser retirado desses bancos.
sugestão: banks_and_values_withdraw
"""

def transfer(request, banks_and_values_withdraw, value_to_transfer, bank_to_transfer, client_to_transfer):
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        try:
            banks = Bank.objects.all()
            bank_client = Client.objects.get(username=request.user)
            bank_list = Bank.objects.all()

            logging.debug(f"logo no inicio\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")

            ## Inicia transação do Two Phase Locking, bloqueando todas as contas.

            if bank_client.in_transaction:
                messages.error(request, "Cliente está em transação no momento. Aguarde.")
                return redirect('transaction_page')

            #{ip: saldo_bloqueado}
            balances_from_other_banks = lock_all_banks(banks, value_to_transfer, bank_client, bank_to_transfer[0]) #accounts[bank.ip] = response.json.get('client_object').blocked_balance
            
            if not balances_from_other_banks:
                messages.error(request, "Falha ao bloquear todos os bancos para a transação.")
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                return redirect('transaction_page')
            
            # Verifica se o cliente possui saldo nos bancos
            if 'this' in banks_and_values_withdraw:
                if bank_client.blocked_balance < Decimal(banks_and_values_withdraw['this']):
                    messages.error(request, "Não há saldo suficiente para efetuar essa transação.")
                    return redirect('transaction_page')
                
            is_sufficient_funds = verify_balance_otherbanks(banks_and_values_withdraw, balances_from_other_banks)

            if not is_sufficient_funds:
                messages.error(request, "Não há saldo suficiente para efetuar essa transação.")
                return redirect('transaction_page')

            logging.debug(f"depois de verificar saldo nos bancos\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
            
            ## Inicia transação de dois commits. Primeiro commit: PREPARE.
            
            url_request = f'http://{bank_to_transfer[0]}:{bank_to_transfer[1]}/transaction/receive/'

            response = requests.post(url_request, data={'init': 'True', 'value': value_to_transfer, 'client': client_to_transfer}, timeout=5)
            
            if response.status_code != 200 or response.json().get('status') == 'ABORT':
                # se o banco que ta recebendo abortou, os saldos são desbloqueados sem alteração no valor
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                messages.error(request, f"O Banco {bank_to_transfer} precisou abortar a operação.")
                return redirect('transaction_page')

            # Se o banco que ta recebendo confirmou que o cliente existe, os saldos são subtraidos dos outros bancos 
            is_subtracted = subtract_balance_all_banks(bank_client, bank_list, banks_and_values_withdraw)
            if not is_subtracted:
                # Se não conseguiu subtrair o valor, aborta.
                is_returned = return_to_initial_balances(bank_client, bank_list, banks_and_values_withdraw)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                    return redirect('transaction_page')
                unlock_all_banks(bank_list, bank_client, bank_to_transfer[0])
                messages.error(request, f"Operação abortada. Não foi possível subtrair valor de banco.")
                return redirect('transaction_page')

            ## Segundo commit: COMMIT.
            response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
            
            ## Terceiro commit: ROLLBACK.
            if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                # Se o banco receptor não conseguiu responder, retorna o valor inicial para os bancos.
                is_returned = return_to_initial_balances(bank_client, bank_list, banks_and_values_withdraw)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                    return redirect('transaction_page')
                
                # Faz chamada de rollback para o banco receptor.
                rollback_response = requests.post(url_request, data={'rollback': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
                if rollback_response.status_code != 200 or rollback_response.json().get('status') != 'ROLLED BACK':
                    raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer} e falha ao reverter a operação.")
                raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}.")

            logging.debug(f"depois do segundo commit\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
            # desbloqueia os bancos
            unlock_all_banks(banks, bank_client, bank_to_transfer[0])

            logging.debug(f"depois de desbloquear todos bancos\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")

            bank_client.save()

            logging.debug(f"bank_client fora do atomic()\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")

            messages.success(request, f"Valor de R${value_to_transfer} transferido com sucesso!")

            return redirect('transaction_page')
        except ConnectTimeout:
            messages.error(request, f"ConnectTimeout Error: O host {bank_to_transfer[0]} pode estar inacessível ou indisponível. Pode haver um firewall ou configuração de rede que bloqueei a conexão. O serviço na porta {bank_to_transfer[1]} pode não estar em execução ou não estar respondendo. O tempo limite de conexão pode ser muito curto para a rede ou servidor em questão.")
            return redirect('transaction_page')
        except ReadTimeout:
            messages.error(request, f"A leitura dos dados da resposta da requisição excedeu o tempo limite especificado.")
            return redirect('transaction_page')

### Cliente só recebe valor se não estiver em transação. Nesta etapa, o valor já está bloqueado.
# valor já está no blocked_balance, precisa mudar a estratégia de 'balance' = blocked_balance e blocked_balance = 'balance_in_transaction'
@csrf_exempt
def receive(request):
    if request.method == "POST":
        client_to_receive = request.POST.get('client')
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'
        rollback = request.POST.get('rollback', 'False') == 'True'
        init = request.POST.get('init', 'False') == 'True'

        try:    
            bank_client = Client.objects.get(username=client_to_receive)

            logging.debug(f"no receive: sem status\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
            
            if init:
                bank_client.blocked_balance += Decimal(value_to_receive)
                bank_client.save()
                logging.debug(f"no receive: status init\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
                return JsonResponse({'status': 'READY'})

            if commit:
                bank_client.balance += Decimal(value_to_receive)
                bank_client.blocked_balance -= Decimal(value_to_receive)
                bank_client.save()
                logging.debug(f"no receive: status commit\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
                return JsonResponse({'status': 'COMMITTED'})

            if rollback:
                bank_client.blocked_balance -= Decimal(value_to_receive)
                bank_client.save()
                logging.debug(f"no receive: status rollback\nbank_client.blocked_balance: {bank_client.blocked_balance}, bank_client.balance: {bank_client.balance}")
                return JsonResponse({'status': 'ROLLED BACK'})
        
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

