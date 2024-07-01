import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal

# Função que solicita bloqueio de todos os bancos de dados de outros Bancos configurados.
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
                    return False
                accounts[bank.name] = response.json().get('blocked_balance') 
            except (ConnectTimeout, ReadTimeout):
                return False
        else:
            url = f'http://{bank.ip}:{bank.port}/transaction/verify_balance/{client.username}/'
            response = requests.get(url)
            accounts[bank.name] = response.json().get('balance') 

    return accounts

# Solicita desbloqueio de todos os clientes de outros Bancos configurados.
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
            if response.json().get('status') == 'ABORT':
                return False
    return True

# Verifica o saldo do cliente logado em todos os outros bancos.
def verify_balance_otherbanks(banks_and_values_withdraw, balances_from_other_banks):
    for key, value in banks_and_values_withdraw.items():
        if key != 'this':
            if (Decimal(value) > Decimal(balances_from_other_banks[key])):
                return False
    return True

# Solicita a restauração dos saldos iniciais de um cliente dos bancos listados.
# Realiza transações reversas e retorna um status de sucesso ou falha com o banco associado.
def return_to_initial_balances(bank_client, bank_list, banks_and_values_withdraw):
    for key, value in banks_and_values_withdraw.items():
        if key == 'this':
            bank_client.blocked_balance = Decimal(value)
            bank_client.save()
        for bank in bank_list:
            if bank.name == key:
                url = f'http://{bank.ip}:{bank.port}/transaction/return_to_initial_balance/'
                response = requests.post(url, data={'client': bank_client.username, 'value': value}, timeout=5)
                if response.json().get('status') == 'ABORT':
                    return False, bank
                bank_buff = bank
    return True, bank_buff
