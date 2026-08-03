from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("website.urls")),

    path("accounts/", include("accounts.urls")),

    path("api/", include("api_v1.urls")),

    path("wallet/", include("wallet.urls")),

    path("pricing/", include("pricing.urls")),

    
]
