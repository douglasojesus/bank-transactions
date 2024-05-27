from django.shortcuts import render

# Arquivo responsável por lidar com a comunicação entre bancos. Requisições recebidas de outros bancos e requisições a serem feitas para outros bancos.

# Interface makes request
# is_authenticated?
def transfer(request):
    # Implementar view para solicitar requisição a outro banco.
    pass

# Other bank makes request
def receive(request, bank):
    if request.method == "POST":
        ...
    # Implementar view para receber requisição de outro(s) banco(s).
    ...
