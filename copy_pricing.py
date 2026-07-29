import os
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from pricing.models import Pricing
from countries.models import Country
from services.models import Service

# Connect to old SQLite
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get pricing with country/service names from SQLite
cursor.execute("""
    SELECT 
        c.name as country_name, 
        s.name as service_name, 
        p.selling_price, 
        p.provider_cost,
        p.estimated_delivery_time,
        p.is_available,
        p.status
    FROM pricing_pricing p
    JOIN countries_country c ON p.country_id = c.id
    JOIN services_service s ON p.service_id = s.id
""")
rows = cursor.fetchall()

created = 0
skipped = 0

for row in rows:
    country_name, service_name, selling_price, provider_cost, \
    estimated_delivery_time, is_available, status = row
    
    try:
        # Find by name instead of provider_id
        country = Country.objects.get(name=country_name)
        service = Service.objects.get(name=service_name)
        
        pricing, was_created = Pricing.objects.get_or_create(
            country=country,
            service=service,
            defaults={
                'selling_price': selling_price,
                'provider_cost': provider_cost,
                'estimated_delivery_time': estimated_delivery_time or 30,
                'is_available': bool(is_available),
                'status': status or 'active',
            }
        )
        
        if was_created:
            created += 1
        else:
            skipped += 1
            
    except Country.DoesNotExist:
        print(f"Country '{country_name}' not found")
        skipped += 1
    except Service.DoesNotExist:
        print(f"Service '{service_name}' not found")
        skipped += 1

conn.close()

print(f"\nDone! Created: {created}, Skipped: {skipped}")