from django.shortcuts import render, redirect
from accounts.models import Client  # Este cliente do banco
from django.http import HttpResponse, JsonResponse
import requests
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt 
from django.core.serializers import serialize

# Arquivo responsável por lidar com a comunicação entre bancos.
# Requisições recebidas de outros bancos e requisições a serem feitas para outros bancos.
# Interface faz a requisição
def transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer):
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        with transaction.atomic():
            # Captura o cliente deste banco
            # select_for_update garante que a linha do cliente esteja bloqueada durante a transação e evitar condições de corrida.
            bank_client = Client.objects.select_for_update().get(username=request.user)  

            if bank_client.balance < value_to_transfer:
                return HttpResponse("Saldo insuficiente na conta de origem", status=400)

            # Primeira fase: solicitação de commit
            url_request = f'{bank_to_transfer}:8000/transaction/receive/{client_to_transfer}/'
            response = requests.post(url_request, data={'status': 'INIT', 'value': value_to_transfer})

            if response.status_code != 200 or response.json().get('status') == 'ABORT':
                return HttpResponse(f"O Banco {bank_to_transfer} precisou abortar a operação.", status=400)

            # Segunda fase: commit
            bank_client.balance -= value_to_transfer
            bank_client.save()

            # Solicita commit no banco receptor
            response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer})
            if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}")

            return HttpResponse("Transferido com sucesso.")

# Banco receptor faz a requisição
@csrf_exempt
def receive(request, client_to_receive):
    if request.method == "POST":
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'  # Tratar corretamente como booleano

        with transaction.atomic():
            try:
                bank_client = Client.objects.select_for_update().get(username=client_to_receive)
            except Client.DoesNotExist:
                return JsonResponse({'status': 'ABORT'})

            if commit:
                bank_client.balance += float(value_to_receive)
                bank_client.save()
                return JsonResponse({'status': 'COMMITTED'})

            # Resposta de primeira fase
            return JsonResponse({'status': 'READY'})

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)
