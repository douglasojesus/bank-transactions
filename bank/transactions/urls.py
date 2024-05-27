from django.contrib import admin
from django.urls import path, include
from .views import transfer, receive

urlpatterns = [
    path('transfer/', transfer, name='transfer'),
    path('receive/', receive, name='receive'),
]
