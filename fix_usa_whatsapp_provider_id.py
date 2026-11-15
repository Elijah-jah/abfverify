# fix_usa_whatsapp_provider_id.py
#
# 1. Finds "United States" on server1
# 2. Finds WhatsApp pricing variant(s) for it
# 3. Points the chosen variant's provider_meta["provider_id"] at 3535
# 4. Deactivates the other WhatsApp variants so only that one is buyable
#
# Run: python manage.py shell < fix_usa_whatsapp_provider_id.py

from django.db import transaction

DRY_RUN = True          # True = print only. False = apply changes.
NEW_PROVIDER_ID = 3535
SERVER = "server1"
COUNTRY_NAME = "United States"
WHATSAPP_MATCH = "whatsapp"
EXCLUDE_BUSINESS = True  # True = ignore "WhatsApp Business" variants

from countries.models import Country
from services.models import Service   # <-- adjust if your Service model lives in another app
from pricing.models import Pricing

usa = Country.objects.get(server=SERVER, name=COUNTRY_NAME)

variants = list(
    Pricing.objects
    .filter(country=usa, service__name__icontains=WHATSAPP_MATCH, service__server=SERVER)
    .select_related("service")
)

if EXCLUDE_BUSINESS:
    variants = [p for p in variants if "business" not in p.service.name.lower()]

if not variants:
    raise SystemExit("No WhatsApp pricing found for USA on server1 — check the service names.")

print(f"Found {len(variants)} WhatsApp variant(s) for USA:")
for p in variants:
    print(f"  - {p.service.name} | provider_id={p.provider_meta.get('provider_id')} "
          f"| available={p.is_available} | selling={p.selling_price}")

# Pick which row carries 3535: exact "WhatsApp" name if present, otherwise the first variant
target = next((p for p in variants if p.service.name.lower() == "whatsapp"), variants[0])
print(f"\nTarget variant: {target.service.name}")

with transaction.atomic():
    for p in variants:
        if p.id == target.id:
            meta = dict(p.provider_meta or {})
            old = meta.get("provider_id")
            meta["provider_id"] = NEW_PROVIDER_ID
            p.provider_meta = meta
            p.is_available = True
            if not DRY_RUN:
                p.save()
            print(f"[TARGET] {p.service.name}: provider_id {old} -> {NEW_PROVIDER_ID}")
        else:
            p.is_available = False
            if not DRY_RUN:
                p.save(update_fields=["is_available"])
            print(f"[DEACTIVATED] {p.service.name}")

print("\nDone. (DRY RUN — nothing saved.)" if DRY_RUN else "\nSaved.")