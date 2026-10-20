from django.urls import path
from .views import get_price, check_sms, get_countries, get_services
from api_v1 import views

urlpatterns = [
    path("get-price/", get_price, name="get_price"),
    path("check-sms/", check_sms, name="check_sms"),
    path("countries/", get_countries, name="get_countries"),
    path("services/", get_services, name="get_services"),
    path('webhooks/instantnums/', views.instantnums_webhook, name='instantnums_webhook'),
]