from django.urls import path
from .views import home_page, sign_in_page, sign_up_page

urlpatterns = [
    path('', home_page, name='home_page'),
    path('signin/', sign_in_page, name='sign_in_page'),
    path('signup/', sign_up_page, name='sign_up_page'),
]
