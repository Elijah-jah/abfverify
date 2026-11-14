from pricing.models import Pricing, PricingConfiguration
from services.models import Service
from countries.models import Country
from providers.smsbower import SMSBowerProvider

config = PricingConfiguration.objects.first()
print("=== CONFIG ===")
print("exchange_rate:", config.exchange_rate, "| fixed_profit:", config.fixed_profit)

print()
print("=== ALL WHATSAPP-LIKE SERVICES ON server1 ===")
for s in Service.objects.filter(server="server1", name__icontains="whats"):
    print(f"id={s.id} code={s.code!r} name={s.name!r} status={s.status}")

print()
print("=== PRICING ROWS FOR CODE 'wa' (main markets) ===")
rows = (Pricing.objects
        .filter(service__server="server1", service__code="wa")
        .select_related("country", "service"))
for p in rows:
    if p.country.name in ("Nigeria", "United States", "United Kingdom", "Ghana", "India"):
        usd = (p.provider_cost / config.exchange_rate) if config.exchange_rate else 0
        expected = p.provider_cost + config.fixed_profit
        flag = "OK" if p.selling_price == expected else f"MISMATCH (expected {expected})"
        print(f"{p.country.name:18} cost_ngn={p.provider_cost} (~${usd:.3f}) sell={p.selling_price} avail={p.is_available} [{flag}]")

print()
print("=== LIVE SMSBOWER WHOLESALE PRICE FOR 'wa' ===")
provider = SMSBowerProvider()
for c in Country.objects.filter(server="server1", name__in=["Nigeria", "United States", "United Kingdom", "Ghana", "India"]):
    try:
        prices = provider.get_prices_by_country_id(c.provider_id)
        print(c.name, "->", prices.get("wa"))
    except Exception as e:
        print(c.name, "ERROR:", e)
