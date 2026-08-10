import os
import sys
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Prevent scheduler from starting in Django's auto-reloader process (local dev only)
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        # Skip during migrations, collectstatic, shell, test, etc.
        if len(sys.argv) > 1 and sys.argv[1] in ('migrate', 'makemigrations', 'collectstatic', 'shell', 'test'):
            return

        try:
            from .jobs import scheduler
            scheduler.start()
            print("=" * 50)
            print("APScheduler STARTED")
            print("=" * 50)
        except Exception as e:
            print(f"APScheduler failed to start: {e}")