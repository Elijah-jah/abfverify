from django.urls import path
from . import views

urlpatterns = [
    path("services/", views.services_view, name="services"),
    path("buy-logs/purchase/<int:product_id>/", views.purchase_log, name="purchase_log"),
]