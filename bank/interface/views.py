from django.shortcuts import render, redirect
from .forms import FormClient

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

# User sign in page
def sign_in_page(request):
    context = {}
    return render(request, 'sign_in_page.html', context=context)

# User sign up page
def sign_up_page(request):
    if request.method == 'POST':
        form = FormClient(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home_page')  # Redireciona para a página inicial após salvar com sucesso
    else:
        form = FormClient()
    context = {'form': form}
    return render(request, 'sign_up_page.html', context=context)

# is_athenticated?
def my_account(request):
    pass