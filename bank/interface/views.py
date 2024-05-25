from django.shortcuts import render

# Create your views here.
def home_page(request):
    context = {}
    return render(request, 'home_page.html', context=context)

def login_page(request):
    context = {}
    return render(request, 'login_page.html', context=context)