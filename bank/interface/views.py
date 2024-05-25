from django.shortcuts import render
from .forms import FormClient

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

def sign_in_page(request):
    context = {}
    return render(request, 'sign_in_page.html', context=context)

def sign_up_page(request):
    context = {}
    return render(request, 'sign_up_page.html', context=context)