from django.urls import path
from .views import transfer, receive, lock, unlock

urlpatterns = [
    path('lock/', lock, name='lock'),
    path('unlock/', unlock, name='unlock'),
    path('transfer/', transfer, name='transfer'),
    path('receive/', receive, name='receive'),
]
