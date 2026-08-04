from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),

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
    
]
