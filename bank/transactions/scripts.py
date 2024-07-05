import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
import logging
from django.contrib import messages
from accounts.models import Client

# Função que solicita bloqueio de todos os bancos de dados de outros Bancos configurados.
def lock_all_banks(bank_list, value, client, ip_bank_to_transfer):
    # bloqueando a conta deste banco
    client.blocked_balance += Decimal(client.balance)
    client.balance = 0
    client.in_transaction = True
    client.save()
    # bloqueando a conta conjunta deste banco
    client_joint_account_user_one = Client.objects.filter(user_one=client.username).first()
    if client_joint_account_user_one is not None:
        client_joint_account_user_one.blocked_balance += Decimal(client_joint_account_user_one.balance)
        client_joint_account_user_one.balance = 0
        client_joint_account_user_one.in_transaction = True
        client_joint_account_user_one.save()
    client_joint_account_user_two = Client.objects.filter(user_two=client.username).first()
    if client_joint_account_user_two is not None:
        client_joint_account_user_two.blocked_balance += Decimal(client_joint_account_user_two.balance)
        client_joint_account_user_two.balance = 0
        client_joint_account_user_two.in_transaction = True
        client_joint_account_user_two.save()

    accounts = {}
    for bank in bank_list:

        if (bank.name != 'this'): # Só bloqueia os bancos que vão enviar dinheiro e não o banco que está coordenando. 
            url = f'http://{bank.ip}:{bank.port}/transaction/lock/'
            logging.debug(f"{url}")
            try:
                response = requests.post(url, data={'value': value, 'client': client.username}, timeout=5)
                if response.status_code != 200 or response.json().get('status') != 'LOCKED':
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
    client.balance = client.blocked_balance
    client.blocked_balance = Decimal(0)
    client.in_transaction = False
    client.save()
    # desbloqueando a conta conjunta deste banco
    client_joint_account_user_one = Client.objects.filter(user_one=client.username).first()
    if client_joint_account_user_one is not None:
        client_joint_account_user_one.balance = client_joint_account_user_one.blocked_balance
        client_joint_account_user_one.blocked_balance = Decimal(0)
        client_joint_account_user_one.in_transaction = False
        client_joint_account_user_one.save()
    client_joint_account_user_two = Client.objects.filter(user_two=client.username).first()
    if client_joint_account_user_two is not None:
        client_joint_account_user_two.balance = client_joint_account_user_two.blocked_balance
        client_joint_account_user_two.blocked_balance = Decimal(0)
        client_joint_account_user_two.in_transaction = False
        client_joint_account_user_two.save()

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
        if key == 'this':
            # subtrai inclusive desse banco atual se houver
            logging.debug(f'ta subtraindo aqui? {bank_client.blocked_balance}')
            bank_client.blocked_balance -= Decimal(value)
            logging.debug(f'ta subtraindo aqui? {bank_client.blocked_balance}')
            bank_client.save()
        elif key.split('_')[0] == 'this': # se for uma conta conjunta neste banco
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
        

