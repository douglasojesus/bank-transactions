from django.urls import path
from .views import transfer, receive, lock, unlock, get_user_info

urlpatterns = [
    path('lock/', lock, name='lock'),
    path('unlock/', unlock, name='unlock'),
    path('transfer/', transfer, name='transfer'),
    path('receive/', receive, name='receive'),
    path('get_user_info/', get_user_info, name='get_user_info'),
]
