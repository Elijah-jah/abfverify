from django.core.management.base import BaseCommand
from services.models import Service


class Command(BaseCommand):
    help = "Sync DaisySMS services from API"

    def handle(self, *args, **kwargs):
        from providers.factory import get_provider
        
        try:
            provider = get_provider("server2")
            services = provider.get_services()
            
            created_count = 0
            for svc in services:
                obj, created = Service.objects.get_or_create(
                    code=svc["code"],
                    server="server2",
                    defaults={"name": svc["name"]}
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Created: {svc['name']} ({svc['code']})"))
                else:
                    if obj.name != svc["name"]:
                        obj.name = svc["name"]
                        obj.save()
                        self.stdout.write(f"Updated: {svc['name']} ({svc['code']})")
            
            self.stdout.write(self.style.SUCCESS(f"\nDone! Created {created_count} new services."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))