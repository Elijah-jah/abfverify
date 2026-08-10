from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


urlpatterns = [
    path('semilore/', admin.site.urls),

    path("", include("website.urls")),

    path("accounts/", include("accounts.urls")),

    path("api/", include("api_v1.urls")),

    path("wallet/", include("wallet.urls")),

    path("pricing/", include("pricing.urls")),

     # Google Search Console verification
    path('googlef0f70b255124184e.html', TemplateView.as_view(
        template_name='googlef0f70b255124184e.html',
        content_type='text/html'
    )),

    # Sitemap
    path('sitemap.xml', TemplateView.as_view(
        template_name='sitemap.xml',
        content_type='application/xml'
    )),
    
    # Robots.txt
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    )),
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
