from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="finance_dashboard"),
    path("sms-recharge/", views.add_sms_recharge, name="add_sms_recharge"),
    path("boost-funding/", views.add_boost_funding, name="add_boost_funding"),
    path("log-batch/", views.add_log_batch, name="add_log_batch"),
    path("record-restock/", views.record_untracked_restock, name="record_untracked_restock"),
]
