from django.contrib import admin
from django.urls import path, include
from interface.views import home_page, flush, create_test
from transactions.views import configure, get_user_info

urlpatterns = [
    path('admin/', admin.site.urls),
    path('configure/', configure, name="configure_page"),
    path('', home_page, name='home_page'),
    path('interface/', include('interface.urls')),
    path('auth/', include('auth_service.urls')),
    path('transaction/', include('transactions.urls')),
    path('get_user_info/', get_user_info, name='get_user_info'),
    path('flush/', flush, name="flush"),
    path('create_test', create_test, name="create_test")
]
