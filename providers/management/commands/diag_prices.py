from django.core.management.base import BaseCommand
from django.db.models import Count

from pricing.models import Pricing


class Command(BaseCommand):
    help = "Diagnose where WhatsApp pricing rows actually point."

    def handle(self, *args, **options):
        qs = Pricing.objects.filter(service__server="server1", service__code="WhatsApp")
        self.stdout.write(f"total WhatsApp price rows: {qs.count()}")
        self.stdout.write(f"distinct service ids: {qs.values_list('service_id', flat=True).distinct().count()}")
        self.stdout.write(f"distinct country ids: {qs.values_list('country_id', flat=True).distinct().count()}")
        self.stdout.write("rows grouped by country server:")
        for row in qs.values("country__server").annotate(n=Count("id")):
            self.stdout.write(f"  {row['country__server']}: {row['n']}")