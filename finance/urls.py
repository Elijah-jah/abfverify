
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="finance_dashboard"),
    path("analytics/", views.analytics, name="finance_analytics"),
    path("inventory/", views.inventory, name="finance_inventory"),
    path("rewards/", views.rewards, name="finance_rewards"),
    path("sms-recharge/", views.add_sms_recharge, name="add_sms_recharge"),
    path("boost-funding/", views.add_boost_funding, name="add_boost_funding"),
    path("log-batch/", views.add_log_batch, name="add_log_batch"),
    path("record-restock/", views.record_untracked_restock, name="record_untracked_restock"),
    path("gift-orders/", views.gift_orders, name="finance_gift_orders"),
    path("gift-orders/<int:pk>/update/", views.gift_order_update, name="finance_gift_order_update"),
    path("gift-orders/<int:pk>/photos/<int:index>/download/", views.gift_order_photo_download, name="finance_gift_order_photo_download"),
    path("gift-orders/<int:pk>/download/", views.gift_order_images_download, name="finance_gift_order_download"),
]