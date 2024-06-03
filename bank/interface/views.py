from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import TransactionForm
from transactions.views import transfer
from accounts.models import Client
from django.contrib import messages

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
    
def transaction_page(request):
    if (not(request.user.is_authenticated)):
        return redirect('sign_in_page')
    else:
        user = Client.objects.filter(username=request.user.username).first()

        if request.method == 'POST':
            form = TransactionForm(request.POST)
            if form.is_valid(): 
                action = request.POST.get('choice')
                if action == 'transfer':
                    value_to_transfer = form.cleaned_data['value_to_transfer']
                    ip_to_transfer = form.cleaned_data['ip_to_transfer']
                    port_to_transfer = form.cleaned_data['port_to_transfer']
                    client_to_transfer = form.cleaned_data['client_to_transfer']
                    if ip_to_transfer and port_to_transfer and client_to_transfer:
                        bank_to_transfer = (ip_to_transfer, port_to_transfer)
                        # Redireciona para a função de transferência existente em transactions
                        response = transfer(request, value_to_transfer, bank_to_transfer, client_to_transfer)
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

        return render(request, 'transaction_page.html', {'form': form, 'user': user})


