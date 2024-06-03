from django.urls import path
from .views import transfer, receive

urlpatterns = [
    path('transfer/', transfer, name='transfer'),
    path('receive/', receive, name='receive'),
]