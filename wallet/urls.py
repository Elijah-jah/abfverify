from django.urls import path
from . import views
from .views import transactions_page

urlpatterns = [

    path("",views.wallet_page,name="wallet"),

    path("fund/",views.fund_wallet,name="fund_wallet"),

     path("verify/",views.verify_payment,name="verify_payment"),

     path("transactions/", transactions_page, name="transactions_page"),

]