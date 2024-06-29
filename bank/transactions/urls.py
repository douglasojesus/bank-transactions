from django.urls import path
from .views import transfer, receive, lock, unlock, get_user_info, subtract, return_to_initial_balance, verify_balance

urlpatterns = [
    path('lock/', lock, name='lock'),
    path('unlock/', unlock, name='unlock'),
    path('transfer/', transfer, name='transfer'),
    path('receive/', receive, name='receive'),
    path('get_user_info/', get_user_info, name='get_user_info'),
    path('subtract/', subtract, name="subtract"),
    path('return_to_initial_balance/', return_to_initial_balance, name="return_to_initial_balance"),
    path('verify_balance/<str:username>/', verify_balance, name='verify_balance'),
]
