"""
Django settings for config project.
"""

from pathlib import Path
from decouple import config
import dj_database_url
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", cast=bool, default=False)

ALLOWED_HOSTS = ['abfverify.com', 'abfverify.onrender.com', 'localhost', '127.0.0.1']

# CRITICAL: Required for HTTPS POST requests on Django 4.0+
CSRF_TRUSTED_ORIGINS = ['https://abfverify.onrender.com']

INSTALLED_APPS = [
    "jazzmin",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "accounts",
    "countries",
    "services",
    "pricing", 
    'wallet.apps.WalletConfig',
    "api_v1",
    "website",
    "orders",
    "providers",
    'django_apscheduler',
    'django_ratelimit',
]

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25

# FIX #1: WhiteNoise MUST be right after SecurityMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # FIXED POSITION
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
]


# config/settings.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Silence django-ratelimit strict checks (safe for single-worker setups)
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "wallet.context_processors.wallet_balance",
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default=''),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default='5432'),
    }
}

db_url = config("DATABASE_URL", default="")
if db_url:
    DATABASES["default"] = dj_database_url.parse(db_url)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise storage
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (NOTE: Render's filesystem is ephemeral — uploads disappear on redeploy)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "accounts.User"

# API Keys
INSTANTNUMS_API_KEY = config("INSTANTNUMS_API_KEY")
INSTANTNUMS_BASE_URL = config("INSTANTNUMS_BASE_URL")
DAISYSMS_API_KEY = config("DAISYSMS_API_KEY", default="")
PAYSTACK_PUBLIC_KEY = config("PAYSTACK_PUBLIC_KEY")
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY")
PAYSTACK_CALLBACK_URL = config("PAYSTACK_CALLBACK_URL")

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# FIX #2: Tell Django to trust Render's HTTPS proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# FIX #3: Redirect HTTP to HTTPS (safe with the line above)
SECURE_SSL_REDIRECT = True

# FIX #4: HTTPS-only cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Jazzmin settings (unchanged)
JAZZMIN_SETTINGS = {
    "site_title": "ABFverify Admin",
    "site_header": "ABFverify",
    "site_brand": "ABFverify",
    "welcome_sign": "Welcome to ABFverify Administration",
    "copyright": "ABFverify",
    "site_logo": "images/mylogo1.png",
    "login_logo": "images/mylogo1.png",
    "site_icon": "images/mylogo1.png",
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "order_with_respect_to": [
        "accounts", "wallet", "countries", "services", 
        "pricing", "orders", "payments", "auth",
    ],
    "icons": {
        "accounts.User": "fas fa-users",
        "accounts.UserSettings": "fas fa-user-cog",
        "wallet.Wallet": "fas fa-wallet",
        "wallet.Transaction": "fas fa-money-check-dollar",
        "countries.Country": "fas fa-globe-africa",
        "services.Service": "fas fa-mobile-screen",
        "pricing.Pricing": "fas fa-tags",
        "orders.Order": "fas fa-cart-shopping",
        "auth.Group": "fas fa-user-group",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-dark",
    "accent": "accent-info",
    "sidebar": "sidebar-dark-info",
    "brand_colour": "navbar-info",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_child_indent": True,
    "sidebar_fixed": True,
    "navbar_fixed": True,
    "footer_fixed": False,
    "layout_boxed": False,
}

