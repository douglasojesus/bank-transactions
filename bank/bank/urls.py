from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('interface/', include('interface.urls')),
    path('auth/', include('auth_service.urls')),
    path('transaction/', include('transactions.urls')),
]
