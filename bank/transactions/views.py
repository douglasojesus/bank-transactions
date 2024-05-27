from django.shortcuts import render
from accounts. models import Client # This bank client
from django.http import HttpResponse
import requests

# Implementar a API aqui.

# Arquivo responsável por lidar com a comunicação entre bancos. Requisições recebidas de outros bancos e requisições a serem feitas para outros bancos.


# Interface makes request
# is_authenticated?
def transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer):
    # Implementar view para solicitar requisição a outro banco.
    bank_client = Client.objects.filter(username=request.user) # Catch this bank client
    if bank_client.balance < value_to_transfer:
        pass # return error
    # make request to another bank


    pass

# Other bank makes request
def receive(request, bank):
    if request.method == "POST":
        ...
    # Implementar view para receber requisição de outro(s) banco(s).
    ...
