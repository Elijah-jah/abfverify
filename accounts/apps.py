import os
import sys
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Prevent scheduler from starting in Django's auto-reloader process
        if os.environ.get('RUN_MAIN') != 'true':
            return

        # Only start scheduler during runserver, not migrate/collectstatic/etc
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