from django.urls import path

from .views import get_live_price

urlpatterns = [
    path(
        "live-price/",
        get_live_price,
        name="live_price",
    ),
]