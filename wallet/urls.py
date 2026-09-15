from django.urls import path
from . import views
from .views import transactions_page

urlpatterns = [

    path("", views.wallet_page, name="wallet"),

    path("transactions/", transactions_page, name="transactions_page"),

    path("account-details/", views.add_account_details, name="add_account_details"),

    path("webhook/pocketfi/", views.pocketfi_webhook, name="pocketfi_webhook"),

]