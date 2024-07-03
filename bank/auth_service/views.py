from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model, logout as auth_logout
from django.contrib import messages
from django.http import HttpResponse
from .forms import FormCreateClient, FormLoginClient, FormCreateJointAccount
from .backend import AuthBackEnd
import logging

logging.basicConfig(level=logging.DEBUG)  # Configura o nível de log para DEBUG

# User sign in page
def sign_in_page(request):
    if request.method == 'POST':
        form = FormLoginClient(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            auth = AuthBackEnd()
            user = auth.authenticate(username=username, password=password) 
            
            if user:
                login(request, user)
                return redirect('my_account_page')
            else:
                # Isso adiciona a mensagem à lista de mensagens do request atual.
                messages.error(request, "Tente novamente. Credenciais incorretas.")
    else:
        form = FormLoginClient()
    context = {'form': form}
    # A message é automaticamente incluída no contexto do template, mesmo que não seja passada explicitamente. 
    return render(request, 'sign_in_page.html', context=context)

def logout_page(request):
    auth_logout(request)
    return redirect('home_page')

# User sign up page
def sign_up_page(request):
    if request.method == 'POST':
        form = FormCreateClient(request.POST)
        if form.is_valid():
            User = get_user_model()
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']  

            User.objects.create_user(first_name=first_name, last_name=last_name,
                                     email=email, username=username, password=password)

            return redirect('home_page')  # Redireciona para a página inicial após salvar com sucesso
    else:
        form = FormCreateClient()
    context = {'form': form}
    return render(request, 'sign_up_page.html', context=context)

# criar página html para o usuário inserir o username da outra pessoa que vai participar. os dois usuários precisam ter conta neste banco.
# retornar para o usuário o login e senha para a conta conjunta (primeiro_user_name+segundo_user_name)
# configurar que se for conta conjunta, ela pode ser acessada através da conta dos 2 usuários que a pertecem.
# então precisa ter um campo para user_one e user_two, com o username ou referencia aos usuários

def create_joint_account(request):
    if request.method == 'POST':
        form = FormCreateJointAccount(request.POST)
        logging.debug(f"{form.errors}")
        if form.is_valid():
            User = get_user_model()
            
            email = form.cleaned_data['email']
            user_two = form.cleaned_data['second_person_username']
            password = form.cleaned_data['password']
            user_one = request.user.username
            username = user_one + user_two
            first_name = 'Conta Conjunta ' +  username
            last_name = ''
            is_joint_account = True

            if user_one == user_two:
                messages.error(request, "Você não pode criar uma conta conjunta com você mesmo.")
                return redirect('create_joint_account')
            
            joint_account_already_exists = User.objects.filter(username=username).exists()

            if joint_account_already_exists:
                messages.error(request, f"Você já tem uma conta conjunta com essa pessoa. Username da conta: {username}")
                return redirect('create_joint_account')
            
            email_already_saved = User.objects.filter(email=email).exists()

            if email_already_saved:
                messages.error(request, f"Você já tem uma conta com esse e-mail. Você deve inserir outro.")
                return redirect('create_joint_account')

            try:
                exists_user_two = User.objects.get(username=user_two)
                if exists_user_two:
                    User.objects.create_user(first_name=first_name, last_name=last_name, 
                                     email=email, username=username, password=password, is_joint_account=is_joint_account, 
                                     user_one=user_one, user_two=user_two)
                messages.success(request, f"Conta conjunta criada com sucesso. Username da nova conta: {username}")
                return redirect('home_page')
            except User.DoesNotExist:
                messages.error(request, "O segundo usuário a ter conta conjunta com você precisa ter conta neste banco.")
                return redirect('create_joint_account')
    else:
        form = FormCreateJointAccount()
    context = {'form': form}
    return render(request, 'create_joint_account_page.html', context=context)