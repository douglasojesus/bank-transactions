from django.shortcuts import render

# Create your views here.
def transfer(request, bank):
    # Implementar view para solicitar requisição a outro banco.
    pass

# Create your views here.
def receive(request, bank):
    if request.method == "POST":
        ...
    # Implementar view para receber requisição de outro(s) banco(s).
    ...