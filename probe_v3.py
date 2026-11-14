import json
from providers.smsbower import SMSBowerProvider

p = SMSBowerProvider()

print("=== V3 per-provider prices: WhatsApp, United States (187) ===")
d = p._request("getPricesV3", service="wa", country="187")
print(json.dumps(d, indent=1)[:3000])

print()
print("=== V3 per-provider prices: WhatsApp, United States virtual (12) ===")
d = p._request("getPricesV3", service="wa", country="12")
print(json.dumps(d, indent=1)[:3000])

print()
print("=== Top countries for WhatsApp (partner view) ===")
d = p._request("getTopCountriesByService", service="wa")
print(json.dumps(d, indent=1)[:2000])
