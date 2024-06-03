from django.shortcuts import redirect
from accounts.models import Client  # Este cliente do banco
from django.http import HttpResponse, JsonResponse
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
from django.contrib import messages

# Arquivo responsável por lidar com a comunicação entre bancos.
# Requisições recebidas de outros bancos e requisições a serem feitas para outros bancos.
# Interface faz a requisição.
def transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer): #bank_to_transfer = (ip, porta)
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        with transaction.atomic():
            # Captura o cliente deste banco
            # select_for_update garante que a linha do cliente esteja bloqueada durante a transação e evitar condições de corrida.
            bank_client = Client.objects.select_for_update().get(username=request.user)  

            if bank_client.balance < value_to_transfer:
                messages.error(request, "Saldo insuficiente na conta de origem.")
                return redirect('transaction_page')

            url_request = f'http://{bank_to_transfer[0]}:{bank_to_transfer[1]}/transaction/receive/'

            print('url_request', url_request)

            try:
            # Primeira fase: solicitação de commit
                response = requests.post(url_request, data={'status': 'INIT', 'value': value_to_transfer, 'client': client_to_transfer}, timeout=5)
            except ConnectTimeout:
                messages.error(request, f"ConnectTimeout Error: O host {bank_to_transfer[0]} pode estar inacessível ou indisponível. Pode haver um firewall ou configuração de rede que bloqueei a conexão. O serviço na porta {bank_to_transfer[1]} pode não estar em execução ou não estar respondendo. O tempo limite de conexão pode ser muito curto para a rede ou servidor em questão.")
                return redirect('transaction_page')
            except ReadTimeout:
                messages.error(request, f"A leitura dos dados da resposta da requisição excedeu o tempo limite especificado.")
                return redirect('transaction_page')

            if response.status_code != 200 or response.json().get('status') == 'ABORT':
                return HttpResponse(f"O Banco {bank_to_transfer} precisou abortar a operação.", status=400)

            # Segunda fase: commit
            bank_client.balance -= value_to_transfer
            bank_client.save()

            # Solicita commit no banco receptor
            response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer})

            if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                # Tentar reverter a transação no banco receptor
                rollback_response = requests.post(url_request, data={'rollback': 'True', 'value': value_to_transfer})
                if rollback_response.status_code != 200 or rollback_response.json().get('status') != 'ROLLED BACK':
                    raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer} e falha ao reverter a operação.")
                raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}.")
            
            return HttpResponse("Transferido com sucesso.")

# Permite que a view receive aceite requisições POST sem a verificação do token CSRF
@csrf_exempt
def receive(request):
    # se for do mesmo banco, o banco de dados pode estar bloqueado this is a bug!
    if request.method == "POST":
        print("recebi a requisição do tipo post")
        client_to_receive = request.POST.get('client')
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'
        rollback = request.POST.get('rollback', 'False') == 'True'

        with transaction.atomic():
            try:
                bank_client = Client.objects.select_for_update().get(username=client_to_receive)
            except Client.DoesNotExist:
                return JsonResponse({'status': 'ABORT'})

            if commit:
                bank_client.balance += Decimal(value_to_receive)
                bank_client.blocked_balance -= Decimal(value_to_receive)

                bank_client.save()
                return JsonResponse({'status': 'COMMITTED'})

            if rollback:
                bank_client.balance -= Decimal(value_to_receive)
                bank_client.save()
                return JsonResponse({'status': 'ROLLED BACK'})

            # Primeira fase: bloquear o valor
            bank_client.blocked_balance += Decimal(value_to_receive)
            bank_client.save()
            return JsonResponse({'status': 'READY'})

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)
