from django.contrib import admin
from django.urls import path, include
from interface.views import home_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_page, name='home_page'),
    path('interface/', include('interface.urls')),
    path('auth/', include('auth_service.urls')),
    path('transaction/', include('transactions.urls')),
]
