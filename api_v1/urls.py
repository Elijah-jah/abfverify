from django.urls import path
from .views import get_price, check_stock, check_sms, get_countries, get_services

urlpatterns = [
    path("get-price/", get_price, name="get_price"),
    path("check-stock/", check_stock, name="check_stock"),
    path("check-sms/", check_sms, name="check_sms"),
    path("countries/", get_countries, name="get_countries"),
    path("services/", get_services, name="get_services"),
]