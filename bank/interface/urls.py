from django.urls import path
from .views import home_page, my_account_page, transaction_page

urlpatterns = [
    path('', home_page, name='home_page'),
    path('account/', my_account_page, name='my_account_page'),
    path('', transaction_page, name='transaction_page'),
]
