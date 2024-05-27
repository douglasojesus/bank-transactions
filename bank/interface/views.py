from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from .forms import FormCreateClient, FormLoginClient

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

# User sign in page
def sign_in_page(request):
    if request.method == 'POST':
        form = FormLoginClient(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password) 
            if user:
                login(request, user)
                return HttpResponse("Logado com sucesso!")
            else:
                return HttpResponse("Credenciais incorretas.")
    else:
        form = FormLoginClient()
    context = {'form': form}
    return render(request, 'sign_in_page.html', context=context)

# User sign up page
def sign_up_page(request):
    if request.method == 'POST':
        form = FormCreateClient(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home_page')  # Redireciona para a página inicial após salvar com sucesso
    else:
        form = FormCreateClient()
    context = {'form': form}
    return render(request, 'sign_up_page.html', context=context)

# is_athenticated?
def my_account(request):
    pass