from django.shortcuts import redirect
from accounts.models import Client  # Este cliente do banco
from django.http import JsonResponse
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt 
from decimal import Decimal
from django.contrib import messages
from .models import Bank


"""
MUDANÇAS:

- Todos os bancos precisam se conhecer.
- Um cliente logado em um banco A consegue fazer transferência de suas contas do banco B para banco C.
- Quando um cliente logado estiver fazendo uma transação, todos os outros bancos precisam estar bloqueados de fazer transação nessa conta.
- Esse bloqueio pode acontecer por meio de estados. O banco A se comunica com todos os bancos ao mesmo tempo.
- Se o saldo do cliente A for atualizado no banco A, deve ser enviado uma notificação para todos os bancos atualizarem o valor de A.
- Vai ter de trabalhar bastante com gerenciamento de estados, onde esse estado é compartilhado entre todos os bancos. 

"""
def configure():
    #configurar quem são os bancos conhecidos e se conectar com todos
    # para um funcionar, todos tem que estar rodando? 
    
# Arquivo responsável por lidar com a comunicação entre bancos.
# Requisições recebidas de outros bancos e requisições a serem feitas para outros bancos.
# Interface faz a requisição.
def transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer): #bank_to_transfer = (ip, porta)
    if not request.user.is_authenticated:
        return redirect('sign_in_page')
    else:
        try:
            with transaction.atomic():
                # Captura o cliente deste banco
                # select_for_update garante que a linha do cliente esteja bloqueada durante a transação e evitar condições de corrida.
                bank_client = Client.objects.select_for_update().get(username=request.user)  

                if bank_client.balance < value_to_transfer:
                    messages.error(request, "Saldo insuficiente na conta de origem.")
                    return redirect('transaction_page')

                url_request = f'http://{bank_to_transfer[0]}:{bank_to_transfer[1]}/transaction/receive/'

                # Primeira fase: solicitação de commit
                response = requests.post(url_request, data={'status': 'INIT', 'value': value_to_transfer, 'client': client_to_transfer}, timeout=5)
                
                print("passei da primeira fase")

                if response.status_code != 200 or response.json().get('status') == 'ABORT':
                    print("abort?", response.status_code, response.json().get('status'))
                    messages.error(request, f"O Banco {bank_to_transfer} precisou abortar a operação.")
                    return redirect('transaction_page')

                # Segunda fase: commit
                bank_client.balance -= value_to_transfer
                bank_client.save()

                # Solicita commit no banco receptor
                response = requests.post(url_request, data={'commit': 'True', 'value': value_to_transfer, 'client': client_to_transfer})

                if response.status_code != 200 or response.json().get('status') != 'COMMITTED':
                    # Tentar reverter a transação no banco receptor
                    rollback_response = requests.post(url_request, data={'rollback': 'True', 'value': value_to_transfer, 'client': client_to_transfer})
                    if rollback_response.status_code != 200 or rollback_response.json().get('status') != 'ROLLED BACK':
                        print(rollback_response.status_code, rollback_response.json().get('status'))
                        raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer} e falha ao reverter a operação.")
                    raise Exception(f"Falha ao confirmar a transação no Banco {bank_to_transfer}.")
                
                messages.success(request, f"Valor de R${value_to_transfer} transferido com sucesso!")
                return redirect('transaction_page')
        except ConnectTimeout:
            messages.error(request, f"ConnectTimeout Error: O host {bank_to_transfer[0]} pode estar inacessível ou indisponível. Pode haver um firewall ou configuração de rede que bloqueei a conexão. O serviço na porta {bank_to_transfer[1]} pode não estar em execução ou não estar respondendo. O tempo limite de conexão pode ser muito curto para a rede ou servidor em questão.")
            return redirect('transaction_page')
        except ReadTimeout:
            messages.error(request, f"A leitura dos dados da resposta da requisição excedeu o tempo limite especificado.")
            return redirect('transaction_page')


# Permite que a view receive aceite requisições POST sem a verificação do token CSRF
@csrf_exempt
def receive(request):
    print("recebi")
    # se for do mesmo banco, o banco de dados pode estar bloqueado this is a bug!
    if request.method == "POST":
        client_to_receive = request.POST.get('client')
        value_to_receive = request.POST.get('value')
        commit = request.POST.get('commit', 'False') == 'True'
        rollback = request.POST.get('rollback', 'False') == 'True'

        try:
            with transaction.atomic():
                print("inside transaction.atomic")
                print('client_to_receive: ', client_to_receive)
                bank_client = Client.objects.select_for_update().get(username=client_to_receive)
                #bank_client = Client.objects.filter(username=client_to_receive).first()
                print(bank_client, client_to_receive)

                if commit:
                    print("dentro do commit")
                    bank_client.balance += Decimal(value_to_receive)
                    bank_client.blocked_balance -= Decimal(value_to_receive)
                    bank_client.save()
                    return JsonResponse({'status': 'COMMITTED'})

                if rollback:
                    bank_client.balance -= Decimal(value_to_receive)
                    bank_client.save()
                    return JsonResponse({'status': 'ROLLED BACK'})

                print("vou iniciar a primeira fase")
                # Primeira fase: bloquear o valor
                bank_client.blocked_balance += Decimal(value_to_receive)
                bank_client.save()
                print("passei da primeira fase")
                return JsonResponse({'status': 'READY'})
            
        except Client.DoesNotExist:
            todos = Client.objects.all()
            for uni in todos:
                print(uni)
            print("deu exceção. cliente não existe.")
            return JsonResponse({'status': 'ABORT'})

    return JsonResponse({'message': 'Você precisa enviar uma requisição POST'}, status=400)

