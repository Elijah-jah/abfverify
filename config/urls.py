from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('semilore/', admin.site.urls),

    path("", include("website.urls")),

    path("finance/", include("finance.urls")),

    path("", include("marketplace.urls")),

    path("accounts/", include("accounts.urls")),

    path("api/", include("api_v1.urls")),

    path("wallet/", include("wallet.urls")),

    path("accounts/", include("boost.urls")),


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
]

# Serve admin-uploaded media (product images) locally during development.
# In production (DEBUG=False) images come from Cloudinary instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)