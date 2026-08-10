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
    path('dismiss-notice/', views.dismiss_notice, name='dismiss_notice'),
    path('429/', views.ratelimited_error, name='ratelimit_error'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='forgot_password.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='reset_email_sent.html'
    ), name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='reset_password.html',
        success_url='/password-reset-complete/'
    ), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
]