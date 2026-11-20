from django.urls import path

from . import views


urlpatterns = [
    path("gifts/", views.gift_sending, name="gift_sending"),
    path("gifts/order/<int:group_id>/", views.gift_order_create, name="gift_order_create"),
    path("gifts/my-orders/", views.my_gift_orders, name="my_gift_orders"),
]
