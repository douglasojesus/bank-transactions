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
import time
from django.core.cache import cache
import os
import json
from .scripts import lock_all_banks, unlock_all_banks, subtract_balance_all_banks, verify_balance_otherbanks, return_to_initial_balances

logging.basicConfig(level=logging.DEBUG)  # Configura o nível de log para DEBUG

CONFIGURED = False

CACHE_FILE = f'{os.getcwd()}/transactions/'

def write_cache(username, data, cache_file):
    cache_file = CACHE_FILE + cache_file
    cache_data = {username: data}
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)

# Função para ler do arquivo de cache
def read_cache(username, cache_file):
    cache_file = CACHE_FILE + cache_file
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            return cache_data.get(username, None)
    return None

# View responsável por cadastrar bancos ao consórcio. A configuração só é feita uma vez.
@csrf_exempt
def configure(request):
    global CONFIGURED
    if not CONFIGURED:
        if request.method == 'POST':
            names = request.POST.getlist('name[]')
            ips = request.POST.getlist('ip[]')
            portas = request.POST.getlist('port[]')

            for name, ip, porta in zip(names, ips, portas):
                bank = Bank.objects.create(name=name, ip=ip, port=porta)
                bank.save()
                
            CONFIGURED = True
            messages.success(request, "Bancos adicionados ao consórcio. Garanta que nos outros bancos, esses bancos também tenham sido registrados.")
            # talvez fazer requisição para esses bancos para eles salvarem esse banco tbm
            return redirect('home_page')
    else:
        messages.error(request, "Os bancos já foram adicionados ao consórcio uma vez.")
        
    banks = Bank.objects.all()
    return render(request, 'configure.html', {'banks': banks})

# View responsável por retornar o saldo do cliente neste banco.
def verify_balance(request, username):
    cliente = Client.objects.get(username=username)
    return JsonResponse({'balance': cliente.balance}, status=200)

# Subtrai do valor bloqueado o valor a ser transferido deste banco.
@csrf_exempt
def subtract(request):
    if request.method == 'POST':
        logging.debug("ENTREI NO SUBTRACTTTTTTTTTTT")
        client_to_subtract = request.POST.get('client')
        value_to_subtract = request.POST.get('value')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_subtract)
                logging.debug(f"bank_client.blocked_balance = {bank_client.blocked_balance}")
                bank_client.blocked_balance -= Decimal(value_to_subtract)
                logging.debug(f"bank_client.blocked_balance = {bank_client.blocked_balance}")
                bank_client.save()
                return JsonResponse({'status': 'COMMITED'})
        except:
            return JsonResponse({'status': 'ABORT'}, status=404)
    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)


def realize_lock(client, is_joint_account):
    if client.in_transaction:
        return False
    if is_joint_account:
        lock_this_account(client, 'cache_joint.txt')
    client.blocked_balance += Decimal(client.balance)
    client.balance = Decimal(0)
    client.in_transaction = True
    client.save()       
    return True     

# Requisição recebida por outro Banco para bloquear este cliente deste Banco.
# O banco de dados em si não é bloqueado, mas sim o valor na conta do cliente para transação.
# A escolha é bloquear o valor total do saldo do cliente, e não apenas o do valor da transferência.
@csrf_exempt
def lock(request):
    if request.method == "POST":
        logging.debug("Tá recebendo a requisição.")
        client_to_lock = request.POST.get('client')
        value_to_lock = request.POST.get('value')
        try:
            bank_client = Client.objects.select_for_update().get(username=client_to_lock)
            if not realize_lock(bank_client, False):
                return JsonResponse({'status': 'ABORT', 'message': 'IN_TRANSACTION'}, status=404)
            
            # Verificar se o cliente tem uma conta conjunta
            client_joint_account_user_one = Client.objects.filter(user_one=client_to_lock).first()
            client_joint_account_user_one_bb = None
            if client_joint_account_user_one is not None:
                if not realize_lock(client_joint_account_user_one, True):
                    logging.debug(f"está em transação? {client_joint_account_user_two.in_transaction}")
                    return JsonResponse({'status': 'ABORT', 'message': 'IN_TRANSACTION'}, status=404)
                client_joint_account_user_one_bb = client_joint_account_user_one.blocked_balance
                client_joint_account_user_one = client_joint_account_user_one.username
            
            client_joint_account_user_two = Client.objects.filter(user_two=client_to_lock).first()
            client_joint_account_user_two_bb = None
            logging.debug(f"client_joint_account_user_two: {client_joint_account_user_two}")
            if client_joint_account_user_two is not None:
                if not realize_lock(client_joint_account_user_two, True):
                    logging.debug(f"está em transação? {client_joint_account_user_two.in_transaction}")
                    return JsonResponse({'status': 'ABORT', 'message': 'IN_TRANSACTION'}, status=404)
                client_joint_account_user_two_bb = client_joint_account_user_two.blocked_balance
                client_joint_account_user_two = client_joint_account_user_two.username

            json_response = {'status': 'LOCKED', 'client': bank_client.username, 
                                 'blocked_balance': bank_client.blocked_balance,
                                 'client_ja_one': client_joint_account_user_one,
                                 'client_ja_one_bb': client_joint_account_user_one_bb,
                                 'client_ja_two': client_joint_account_user_two,
                                 'client_ja_two_bb': client_joint_account_user_two_bb,
                                }
            logging.debug(f"{json_response}")

            
            return JsonResponse(json_response)
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)
    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)


def realize_unlock(client, is_joint_account):
    if not client.balance: # se tiver balance significa que o cliente tem saldo disponível, então recebeu a transferência, então nao recebe desbloqueio
        client.balance = client.blocked_balance
    if is_joint_account:
        end_transaction(client, 'cache_joint.txt')
    client.blocked_balance = Decimal(0)
    client.in_transaction = False
    client.save()
    return client

# Requisição recebida por outro Banco para desbloquear este cliente deste Banco.
# O banco de dados em si não é debloqueado, mas sim o valor na conta do cliente para transação.
# A escolha é desbloquear o valor total do saldo bloqueado do cliente, e não apenas o do valor da transferência.
@csrf_exempt
def unlock(request):
    # verificar se esse cliente tem conta conjunta nos outros bancos
    # para cada banco, verificar tbm se tem um user_one ou user_two com o username desse client
    if request.method == "POST":
        client_to_unlock = request.POST.get('client')
        try:
            with transaction.atomic():
                bank_client = Client.objects.select_for_update().get(username=client_to_unlock)
                logging.debug("ENTREI NO UNLOCKKKKKKKKKKKKKKK")
                realize_unlock(bank_client)
                client_joint_account_user_one = Client.objects.filter(user_one=client_to_unlock).first()
                if client_joint_account_user_one is not None:
                    logging.debug(f"MEU USERNAME: {client_joint_account_user_one.username}, MEU SALDO ANTES DE DESBLOQUEAR (blocked_balance): {client_joint_account_user_one.blocked_balance}")
                    realize_unlock(client_joint_account_user_one)
                    logging.debug(f"MEU USERNAME: {client_joint_account_user_one.username}, MEU SALDO DEPOIS DE DESBLOQUEAR (blocked_balance): {client_joint_account_user_one.blocked_balance}")

                client_joint_account_user_two = Client.objects.filter(user_two=client_to_unlock).first()
                if client_joint_account_user_two is not None:
                    logging.debug(f"MEU USERNAME: {client_joint_account_user_two.username}, MEU SALDO ANTES DE DESBLOQUEAR (blocked_balance): {client_joint_account_user_two.blocked_balance}")
                    realize_unlock(client_joint_account_user_two)
                    logging.debug(f"MEU USERNAME: {client_joint_account_user_two.username}, MEU SALDO DEPOIS DE DESBLOQUEAR (blocked_balance): {client_joint_account_user_two.blocked_balance}")

                logging.debug(f"{client_joint_account_user_one} - {client_joint_account_user_two} - {client_to_unlock}")

                return JsonResponse({'status': 'UNLOCKED'})
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

# View responsável por retornar se o cliente existe e o saldo.
@csrf_exempt
def get_user_info(request):
    username = request.POST.get('username')
    
    try:
        client = Client.objects.get(username=username)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
    
    response_data = {'balance': client.balance}

    # Verificar se o cliente tem uma conta conjunta
    client_joint_account_user_one = Client.objects.filter(user_one=username).first()
    client_joint_account_user_two = Client.objects.filter(user_two=username).first()
    if client_joint_account_user_one is not None:
        response_data['client_ja_one'] = client_joint_account_user_one.username
        response_data['client_ja_one_bb'] = client_joint_account_user_one.balance
    if client_joint_account_user_two is not None:
        response_data['client_ja_two'] = client_joint_account_user_two.username
        response_data['client_ja_two_bb'] = client_joint_account_user_two.balance
    
    return JsonResponse(response_data, status=200)

# View responsável por atualizar o valor do saldo deste cliente baseado no valor do saldo anterior.
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

def lock_this_account(bank_client, cache_file):
    cache_data = read_cache(bank_client.username, cache_file)
    logging.debug(f'cache_data: {cache_data}')
    if cache_data is not None:
        is_in_transaction = cache_data['in_transaction']
        if is_in_transaction:
            return True
        else:
            logging.debug(f'Cliente não está em transação no cache. Verificando no banco de dados...')
            if bank_client.in_transaction:
                return True
            bank_client.in_transaction = True
            bank_client.save()
            bank_client_cache = {'in_transaction': True}
            write_cache(bank_client.username, bank_client_cache, cache_file)
    else:
        if bank_client.in_transaction:
            return True
        bank_client.in_transaction = True
        bank_client.save()
        bank_client_cache = {'in_transaction': True}
        write_cache(bank_client.username, bank_client_cache, cache_file)

# View que coordena transação deste Banco para os outros Bancos.
# Banco para transferir: bank_to_transfer. Bancos para pegar o valor: banks.
# Esta view pega os valores que o cliente deste Banco quer transferir a partir de outros bancos e transfere para o banco que escolher.

# bank_balance_map : dicionario com os saldos antes das transações
# banks_and_values_withdraw : dicionario com os valores a serem retirado das contas
def transfer(request, banks_and_values_withdraw, value_to_transfer, bank_to_transfer, client_to_transfer, bank_balance_map):
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        try:
            banks = Bank.objects.all()
            bank_client = Client.objects.get(username=request.user)

            logging.debug("passou do primeiro sleep")

            ## Inicia transação do Two Phase Locking, bloqueando todas as contas.
            is_in_transaction = lock_this_account(bank_client, 'cache.txt')
            if is_in_transaction:
                messages.error(request, "Cliente está em transação no momento. Aguarde.")
                return redirect('transaction_page')

            time.sleep(10)

            # Verifica se a soma dos valores que quer transferir de cada banco é igual ao valor que quer transferir total.
            soma = Decimal()
            for key, value in banks_and_values_withdraw.items():
                soma += Decimal(value)
            if soma != value_to_transfer:
                messages.error(request, "A soma dos valores a serem transferidos do banco não é igual ao valor a ser transferido total.")
                return redirect('transaction_page')
            
            # Verifica se a transferência está acontecendo do bancoX para o bancoX
            if (bank_to_transfer[2] in banks_and_values_withdraw) and request.user.username == client_to_transfer:
                messages.error(request, f"O cliente {client_to_transfer} do {bank_to_transfer[2]} não pode transferir para ele mesmo (mesma conta e mesmo banco).")
                return redirect('transaction_page')
            
            #{ip: saldo_bloqueado}
            balances_from_other_banks = lock_all_banks(banks, value_to_transfer, bank_client, bank_to_transfer[0]) #accounts[bank.ip] = response.json.get('client_object').blocked_balance
            balances_from_other_banks = bank_balance_map

            logging.debug(f'balances_from_other_banks: {balances_from_other_banks}')
            if not balances_from_other_banks:
                messages.error(request, "Falha ao bloquear todos os bancos para a transação.")
                is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                    return redirect('transaction_page')
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                return redirect('transaction_page')
            
            # Verifica se o cliente possui saldo nos bancos
            if 'this' in banks_and_values_withdraw:
                if bank_client.blocked_balance < Decimal(banks_and_values_withdraw['this']):
                    messages.error(request, "Não há saldo suficiente para efetuar essa transação.")
                    return redirect('transaction_page')
                
            is_sufficient_funds = verify_balance_otherbanks(banks_and_values_withdraw, balances_from_other_banks)

            if not is_sufficient_funds:
                is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                end_transaction(bank_client, 'cache.txt')
                messages.error(request, "Não há saldo suficiente para efetuar essa transação.")
                return redirect('transaction_page')
            
            logging.debug("Já passei do sufficient funds")

            ## Inicia transação de dois commits. Primeiro commit: PREPARE.
            
            url_request = f'http://{bank_to_transfer[0]}:{bank_to_transfer[1]}/transaction/receive/'

            response = requests.post(url_request, data={'init': 'True', 'value': value_to_transfer, 'client': client_to_transfer}, timeout=5)
            
            if response.status_code != 200 or response.json().get('status') == 'ABORT':
                # se o banco que ta recebendo abortou, os saldos são desbloqueados sem alteração no valor
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                messages.error(request, f"O Banco {bank_to_transfer} precisou abortar a operação.")
                return redirect('transaction_page')

            logging.debug("Na hora de subtrair")

            # Se o banco que ta recebendo confirmou que o cliente existe, os saldos são subtraidos dos outros bancos 
            is_subtracted = subtract_balance_all_banks(bank_client, banks, banks_and_values_withdraw)
            if not is_subtracted:
                # Se não conseguiu subtrair o valor, aborta.
                is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                    return redirect('transaction_page')
                unlock_all_banks(banks, bank_client, bank_to_transfer[0])
                messages.error(request, f"Operação abortada. Não foi possível subtrair valor de banco.")
                return redirect('transaction_page')
            
            logging.debug("Subtraiu.")

            ## Segundo commit: COMMIT.
            response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
            
            ## Terceiro commit: ROLLBACK.
            if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                logging.debug("rollback é feito! BBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
                # Se o banco receptor não conseguiu responder, retorna o valor inicial para os bancos.
                is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
                if is_returned[0] == False:
                    messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
                    return redirect('transaction_page')
                
                # Faz chamada de rollback para o banco receptor.
                rollback_response = requests.post(url_request, data={'rollback': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
                if rollback_response.status_code != 200 or rollback_response.json().get('status') != 'ROLLED BACK':
                    raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer} e falha ao reverter a operação.")
                raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}.")

            unlock_all_banks(banks, bank_client, bank_to_transfer[0])
            bank_client.save()
            messages.success(request, f"Valor de R${value_to_transfer} transferido com sucesso!")

            end_transaction(bank_client, 'cache.txt')

            return redirect('transaction_page')
        
        except ConnectTimeout:
            is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
            if is_returned[0] == False:
                messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
            unlock_all_banks(banks, bank_client, bank_to_transfer[0])
            messages.error(request, f"ConnectTimeout Error: O host {bank_to_transfer[0]} pode estar inacessível ou indisponível. Pode haver um firewall ou configuração de rede que bloqueei a conexão. O serviço na porta {bank_to_transfer[1]} pode não estar em execução ou não estar respondendo. O tempo limite de conexão pode ser muito curto para a rede ou servidor em questão.")
            end_transaction(bank_client, 'cache.txt')
            return redirect('transaction_page')
        
        except ReadTimeout:
            is_returned = return_to_initial_balances(bank_client, banks, bank_balance_map)
            if is_returned[0] == False:
                messages.error(request, f"O banco {is_returned[1]} não conseguiu retornar o valor para a conta depois do erro de transação.")
            unlock_all_banks(banks, bank_client, bank_to_transfer[0])
            messages.error(request, f"A leitura dos dados da resposta da requisição excedeu o tempo limite especificado.")
            end_transaction(bank_client, 'cache.txt')
            return redirect('transaction_page')
        
def end_transaction(bank_client, cache_file):
    cache_data = read_cache(bank_client.username, cache_file)
    if cache_data is not None:
        cache_data['in_transaction'] = False
        write_cache(bank_client.username, cache_data, cache_file)


### Cliente só recebe valor se não estiver em transação. Nesta etapa, o valor já está bloqueado.
# valor já está no blocked_balance, precisa mudar a estratégia de 'balance' = blocked_balance e blocked_balance = 'balance_in_transaction'
@csrf_exempt
def receive(request):
    if request.method == "POST":
        logging.debug("recebi o receive AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        client_to_receive = request.POST.get('client')
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'
        rollback = request.POST.get('rollback', 'False') == 'True'
        init = request.POST.get('init', 'False') == 'True'

        try:
            bank_client = Client.objects.get(username=client_to_receive)
            
            if init:
                bank_client.blocked_balance += Decimal(value_to_receive)
                logging.debug(f"fiz o init AAAAAAAAAAAA blocked: {bank_client.blocked_balance} value: {value_to_receive}")
                bank_client.save()
                return JsonResponse({'status': 'READY'})

            if commit:
                bank_client.balance += Decimal(bank_client.blocked_balance)
                bank_client.blocked_balance -= Decimal(0)
                bank_client.save()
                logging.debug(f"fiz o commit AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA balance: {bank_client.balance} blocked: {bank_client.blocked_balance}")
                return JsonResponse({'status': 'COMMITTED'})

            if rollback:
                bank_client.blocked_balance -= Decimal(value_to_receive)
                bank_client.save()
                return JsonResponse({'status': 'ROLLED BACK'})
        
        except Client.DoesNotExist:
            return JsonResponse({'status': 'ABORT'}, status=404)

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

