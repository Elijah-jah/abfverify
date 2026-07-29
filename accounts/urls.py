from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("services/", views.services_view, name="services"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("wallet/", views.wallet_view, name="wallet"),
    path("orders/", views.orders_view, name="orders"),
    path("sms/", views.sms_view, name="sms"),
    path("settings/", views.settings_view, name="settings"),
    path("transactions/", views.transactions_page, name="transactions"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("cancel-order/", views.cancel_order_view, name="cancel_order"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("terms-of-service/", views.terms_of_service, name="terms_of_service"),
]