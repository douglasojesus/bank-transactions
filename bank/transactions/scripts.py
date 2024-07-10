import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
import logging
from django.contrib import messages
from accounts.models import Client
import os
import json

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

def lock_this_account(bank_client, cache_file):
    cache_data = read_cache(bank_client.username, cache_file)
    if cache_data is not None:
        is_in_transaction = cache_data['in_transaction']
        if is_in_transaction:
            return True
        else:
            if bank_client.in_transaction:
                return True
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

def realize_lock(client, is_joint_account):
    logging.debug(f'lock_this_account: {client}')
    if client.in_transaction:
        return True
    if is_joint_account:
        client.blocked_balance += Decimal(client.balance)
        client.balance = Decimal(0)
        client.save()   
        is_in_transaction = lock_this_account(client, 'cache_joint.txt')
        if is_in_transaction:
            return True
    client.blocked_balance += Decimal(client.balance)
    client.balance = Decimal(0)
    client.in_transaction = True
    client.save()
    logging.debug('to retornando true aqui')
    return False    

def realize_unlock(client, is_joint_account):
    logging.debug(f'unlock_this_account: {client}')
    if not client.balance: # se tiver balance significa que o cliente tem saldo disponível, então recebeu a transferência, então nao recebe desbloqueio
        client.balance = client.blocked_balance
    if is_joint_account:
        end_transaction(client, 'cache_joint.txt')
    client.blocked_balance = Decimal(0)
    client.in_transaction = False
    client.save()
    return client

def end_transaction(bank_client, cache_file):
    cache_data = read_cache(bank_client.username, cache_file)
    if cache_data is not None:
        cache_data['in_transaction'] = False
        write_cache(bank_client.username, cache_data, cache_file)

# Função que solicita bloqueio de todos os bancos de dados de outros Bancos configurados.
def lock_all_banks(bank_list, value, client, ip_bank_to_transfer):
    # bloqueando a conta deste banco
    logging.debug(f'esse cliente ta em transação? {client.in_transaction}')
    is_in_transaction = realize_lock(client, False)
    if is_in_transaction:
        logging.debug(f'ESSE BANCO IS NOT NONE - DEU FALSE AQUI')
        return False
    
    # bloqueando a conta conjunta deste banco
    client_joint_account_user_one = Client.objects.filter(user_one=client.username).first()
    if client_joint_account_user_one is not None:
        is_in_transaction = realize_lock(client_joint_account_user_one, True)
        if is_in_transaction:
            logging.debug(f'client_joint_account_user_ONE IS NOT NONE - DEU FALSE AQUI')
            return False
    client_joint_account_user_two = Client.objects.filter(user_two=client.username).first()
    if client_joint_account_user_two is not None:
        is_in_transaction = realize_lock(client_joint_account_user_two, True)
        if is_in_transaction:
            logging.debug(f'client_joint_account_user_two IS NOT NONE - DEU FALSE AQUI')
            return False

    accounts = {}
    for bank in bank_list:

        if (bank.name != 'this'): # Só bloqueia os bancos que vão enviar dinheiro e não o banco que está coordenando. 
            url = f'http://{bank.ip}:{bank.port}/transaction/lock/'
            logging.debug(f"{url}")
            try:
                response = requests.post(url, data={'value': value, 'client': client.username}, timeout=5)
                logging.debug(f"respostas do lock: {response}")
                if response.status_code != 200 or response.json().get('status') != 'LOCKED':
                    logging.debug(f"{response.status_code} - {response.json().get('status')} - DEU FALSE AQUI")
                    return False
                accounts[bank.name] = response.json().get('blocked_balance') 
                client_ja_one = response.json().get('client_ja_one')
                if client_ja_one is not None:
                    client_ja_one_bb = response.json().get('client_ja_one_bb')
                    key_dict = bank.name+'_'+client_ja_one
                    accounts[key_dict] = client_ja_one_bb
                client_ja_two = response.json().get('client_ja_two')
                if client_ja_two is not None:
                    client_ja_two_bb = response.json().get('client_ja_two_bb')
                    key_dict = bank.name+'_'+client_ja_two
                    accounts[key_dict] = client_ja_two_bb
            except (ConnectTimeout, ReadTimeout):
                return False
        else:
            accounts['this'] = Client.objects.get(username=client.username).blocked_balance

    return accounts

# Solicita desbloqueio de todos os clientes de outros Bancos configurados.
def unlock_all_banks(bank_list, client, ip_bank_to_transfer):
    realize_unlock(client, False)
    # desbloqueando a conta conjunta deste banco
    client_joint_account_user_one = Client.objects.filter(user_one=client.username).first()
    if client_joint_account_user_one is not None:
        realize_unlock(client_joint_account_user_one, True)
    client_joint_account_user_two = Client.objects.filter(user_two=client.username).first()
    if client_joint_account_user_two is not None:
        realize_unlock(client_joint_account_user_one, True)

    for bank in bank_list:
        url = f'http://{bank.ip}:{bank.port}/transaction/unlock/'
        if (bank.name != 'this'): # Só desbloqueia bancos que enviam e não o banco que está coordenando. 
            try:
                response = requests.post(url, data={'client': client.username}, timeout=5)
            except (ConnectTimeout, ReadTimeout):
                continue

# Solicita subtração dos valores dos bancos que efetuarão a transferência.
def subtract_balance_all_banks(bank_client, bank_list, banks_and_values_withdraw):
    for key, value in banks_and_values_withdraw.items():
        logging.debug(f'banks_and_values_withdraw: {key}')
        if key == 'this':
            # subtrai inclusive desse banco atual se houver
            logging.debug(f'ta subtraindo aqui? {bank_client.blocked_balance}')
            bank_client.blocked_balance -= Decimal(value)
            logging.debug(f'ta subtraindo aqui? {bank_client.blocked_balance}')
            bank_client.save()
        elif key.split('_')[0] == 'this': # se for uma conta conjunta neste banco
            logging.debug('é uma conta conjunta neste banco')
            bank_client = Client.objects.get(username=key.split('_')[1])
            bank_client.blocked_balance -= Decimal(value)
            bank_client.save()
        else:
            for bank in bank_list: # bank_list não tem o nomeDoBanco_joint_account. tem que ver isso
                if bank.name == key or bank.name == key.split('_')[0]:
                    bank_obj = bank
                    break
            url = f'http://{bank_obj.ip}:{bank_obj.port}/transaction/subtract/'

            if bank_client.username in key: # é conta conjunta
                username = key.split('_')[1]
            else:
                username = bank_client.username
            response = requests.post(url, data={'client': username, 'value': value}, timeout=5)
            if response.json().get('status') == 'ABORT':
                return False
    return True

# Verifica o saldo do cliente logado em todos os outros bancos.
def verify_balance_otherbanks(banks_and_values_withdraw, balances_from_other_banks):
    for key, value in banks_and_values_withdraw.items():
        if key != 'this' and key.split('_')[0] != 'this':
            if (Decimal(value) > Decimal(balances_from_other_banks[key])):
                return False
    return True

# Solicita a restauração dos saldos iniciais de um cliente dos bancos listados.
# Realiza transações reversas e retorna um status de sucesso ou falha com o banco associado.
def return_to_initial_balances(bank_client, bank_list, bank_initial_balance):
    bank_buff = ''
    try:
        for key, value in bank_initial_balance.items():
            if key == 'this':
                bank_client.blocked_balance = Decimal(value)
                bank_client.save()
            for bank in bank_list:
                url = f'http://{bank.ip}:{bank.port}/transaction/return_to_initial_balance/'
                logging.debug(f'{url}')
                if bank.name == key:
                    response = requests.post(url, data={'client': bank_client.username, 'value': value}, timeout=5)
                    if response.json().get('status') == 'ABORT':
                        return False, bank
                    bank_buff = bank
                elif bank.name == key.split('_')[0]: # joint_account
                    response = requests.post(url, data={'client': key.split('_')[1], 'value': value}, timeout=5)
                    if response.json().get('status') == 'ABORT':
                        return False, bank
                    bank_buff = bank

        return True, bank_buff
    except (ReadTimeout, ConnectTimeout):
        logging.debug('deu readtimeout no return_to_initial_balances')
        return False, bank_buff
        

