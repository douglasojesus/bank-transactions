from django.urls import path
from .views import home_page, login_page

urlpatterns = [
    path('', home_page, name='home_page'),
    path('login/', login_page, name='login_page'),
]
