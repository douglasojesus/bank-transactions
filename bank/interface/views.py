from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import TransactionForm
from transactions.views import transfer
from accounts.models import Client
from django.contrib import messages
from transactions.models import Bank
from requests.exceptions import ConnectTimeout, ReadTimeout
import requests
from django.contrib.auth import get_user_model
from transactions.views import CONFIGURED


def create_test(request):
    clientes = {'douglas': ["Douglas", "Jesus", "douglas@gmail.com", "1234"],
                'fulano': ["Fulano", "Silva", "fulano@gmail.com", "1234"],
                'ciclano': ["Ciclano", "Santos", "ciclano@gmail.com", "1234"]}
    User = get_user_model()
    User.objects.create_user(first_name=clientes['douglas'][0], last_name=clientes['douglas'][1],
                            email=clientes['douglas'][2], username='douglas', password=clientes['douglas'][3], is_superuser=True)
    User.objects.create_user(first_name=clientes['fulano'][0], last_name=clientes['fulano'][1],
                            email=clientes['fulano'][2], username='fulano', password=clientes['fulano'][3])
    User.objects.create_user(first_name=clientes['ciclano'][0], last_name=clientes['ciclano'][1],
                            email=clientes['ciclano'][2], username='ciclano', password=clientes['ciclano'][3])
    return redirect('home_page')

def flush(request):
    Bank.objects.all().delete()
    Client.objects.all().delete()
    CONFIGURED = False
    return redirect('home_page')

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

# is_athenticated?
def my_account_page(request):
    if (not(request.user.is_authenticated)):
        return redirect('sign_in_page')
    else: 
        return render(request, 'account_page.html', {'user': request.user})
    
def external_client_info(username):
    banks = Bank.objects.all()
    bank_balance_map = {}
    print(banks.first())
    if banks.first():
        for bank in banks:
            url = f'http://{bank.ip}:{bank.port}/get_user_info/'
            print(url)
            #try:
            response = requests.post(url, data={'username': username}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                bank_balance_map[bank.name] = data.get('balance')
            #except (ConnectTimeout, ReadTimeout):
            #    print("deu erro de connecttimeout ou readtimeout")
    return bank_balance_map


# pegar uma string só e fazer quebra da string para ser os valores dos bancos
# deve ser escrito: banco1=1234,banco2=1234,banco3=1234
def transaction_page(request):
    if (not(request.user.is_authenticated)):
        return redirect('sign_in_page')
    else:
        user = Client.objects.filter(username=request.user.username).first()
        # fazer requisições para outros bancos para pegar informações desse cliente
        print("até aqui ta de boa. transaction_page antes de pegar o bank_balance_map")
        print(user.username)
        bank_balance_map = external_client_info(user.username)
        print(bank_balance_map)
        if request.method == 'POST':
            form = TransactionForm(request.POST)
            if form.is_valid(): 
                action = request.POST.get('choice')
                if action == 'transfer':
                    value_to_transfer = form.cleaned_data['value_to_transfer']
                    ip_to_transfer = form.cleaned_data['ip_to_transfer']
                    port_to_transfer = form.cleaned_data['port_to_transfer']
                    client_to_transfer = form.cleaned_data['client_to_transfer']

                    banks_and_values_withdraw = {} #banco: valor

                    banks_values_buffer = request.POST.get("banks_values") # banco1=200,banco2=20
                    print(banks_values_buffer)
                    print(len(banks_values_buffer))
                    key_value_buffer = ''
                    # FAZER FUNÇÃO EM SCRIPTS PARA RETORNAR VALOR 
                    for i in range(len(banks_values_buffer)):
                        if banks_values_buffer[i] == '=':
                            nome_banco = key_value_buffer
                            key_value_buffer = ''
                        elif banks_values_buffer[i] == ',' or i == len(banks_values_buffer):
                            valor_transferencia = key_value_buffer
                            key_value_buffer = ''
                            banks_and_values_withdraw[nome_banco] = valor_transferencia
                            valor_transferencia = ''
                            nome_banco = ''
                        else:
                            key_value_buffer += banks_values_buffer[i]
                    
                    banks_and_values_withdraw[nome_banco] = key_value_buffer

                    # Aqui você pode lidar com o dicionário como necessário
                    print(banks_and_values_withdraw)

                    if ip_to_transfer and port_to_transfer and client_to_transfer:
                        bank_to_transfer = (ip_to_transfer, port_to_transfer)
                        # Redireciona para a função de transferência existente em transactions
                        response = transfer(request, banks_and_values_withdraw, value_to_transfer, bank_to_transfer, client_to_transfer)
                        return response
                    else:
                        messages.error(request, "Você precisa inserir o banco, a agência e o cliente.")
                        return redirect('transaction_page')
                    
                elif action == 'deposit':
                    value_to_transfer = form.cleaned_data['value_to_transfer']
                    user.balance += value_to_transfer
                    user.save()
                    return redirect('my_account_page')

                elif action == 'payment':
                    pass
        else:
            form = TransactionForm()

        return render(request, 'transaction_page.html', {'form': form, 'user': user, 'bank_balance_map': bank_balance_map})


