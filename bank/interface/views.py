from django.shortcuts import render, redirect
from django.http import HttpResponse

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

# is_athenticated?
def my_account_page(request):
    if (not(request.user.is_authenticated)):
        return redirect('sign_in_page')
    else: 
        return HttpResponse("Logado com sucesso!")