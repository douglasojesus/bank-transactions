from django.urls import path
from .views import transfer, receive

urlpatterns = [
    path('transfer/', transfer, name='transfer'),
    path('receive/<str:client_to_receive>/', receive, name='receive'),
]