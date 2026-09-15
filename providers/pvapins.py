import json
import logging
import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class PVAPinsProvider:
    """
    PVAPins adapter — drop-in replacement for InstantNumsProvider.

    - REST v1 (JSON, ISO country codes) for balance/catalog/price/stock/
      purchase/poll.
    - Classic /user/api endpoint for cancel and bulk rates only
      (REST v1 has no cancel, and get_rates is classic-only).
    """

    REST_BASE = "https://api.pvapins.com/api/v1"
    CLASSIC_BASE = "https://api.pvapins.com/user/api"

    def __init__(self):
        self.api_key = settings.PVAPINS_API_KEY
        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    # ---------- internal request helpers ----------

    def _rest(self, method, path, **kwargs):
        url = f"{self.REST_BASE}{path}"
        kwargs.setdefault("timeout", 15)
        kwargs["headers"] = {**self.headers, **kwargs.get("headers", {})}

        try:
            response = requests.request(method, url, **kwargs)
        except requests.Timeout:
            logger.error("PVAPins timeout: %s %s", method, url)
            raise Exception("Provider is taking too long. Please try again.")
        except requests.ConnectionError:
            logger.error("PVAPins connection error: %s %s", method, url)
            raise Exception("Unable to connect to provider. Please try again.")
        except requests.RequestException:
            logger.exception("PVAPins request failed: %s %s", method, url)
            raise Exception("Provider request failed. Please try again.")

        if response.status_code == 429:
            raise Exception("Provider rate limit hit. Please try again shortly.")

        try:
            data = response.json()
        except ValueError:
            logger.error(
                "PVAPins non-JSON response (%s): %s",
                response.status_code,
                response.text[:200],
            )
            raise Exception("Provider returned an unexpected response.")

        if response.status_code >= 400:
            message = data.get("message") or data.get("error") or "Provider error."
            logger.error(
                "PVAPins HTTP %s on %s: %s",
                response.status_code,
                url,
                data,
            )
            raise Exception(str(message))

        return data

    def _classic(self, endpoint, params=None):
        params = dict(params or {})
        params["customer"] = self.api_key
        try:
            response = requests.get(
                f"{self.CLASSIC_BASE}/{endpoint}",
                params=params,
                timeout=15,
            )
            return response.json()
        except requests.RequestException:
            logger.exception("PVAPins classic request failed: %s", endpoint)
            raise Exception("Provider request failed. Please try again.")

    # ---------- provider interface (same as InstantNums) ----------

    def get_balance(self):
        data = self._rest("GET", "/account")
        return {"success": True, "balance": data.get("balance")}

    def get_countries(self):
        data = self._rest("GET", "/countries")
        countries = [
            {"id": c.get("code"), "full_name": c.get("name")}
            for c in data.get("countries", [])
        ]
        return {"success": True, "countries": countries}

    def get_services(self):
        data = self._rest("GET", "/services")
        services = [
            {"code": s.get("code"), "name": s.get("name")}
            for s in data.get("services", [])
        ]
        return {"success": True, "services": services}

    def get_price(self, service, country):
        # service = Service.code (e.g. "wa"), country = Country.iso_code (e.g. "US")
        data = self._rest(
            "GET",
            "/numbers",
            params={"country": str(country).upper(), "service": service},
        )
        price = data.get("price")
        if price is None:
            logger.error(
                "PVAPins price missing for %s/%s: %s",
                service,
                country,
                data,
            )
            raise Exception("Unable to fetch price from provider.")
        return {"success": True, "price_usd": str(price)}

    def check_stock(self, service, country):
        data = self._rest(
            "GET",
            "/numbers",
            params={"country": str(country).upper(), "service": service},
        )
        available = sum(
            int(c["available"])
            for c in data.get("countries", [])
            if c.get("available")
        )
        return {
            "success": True,
            "available": available,
            "in_stock": data.get("price") is not None,
        }

    def get_rates(self, country_name):
        """
        Bulk prices for one country (classic API, ONE call per country).
        Returns: {service_name_lower: price_usd_str}
        """
        data = self._classic("get_rates.php", {"country": country_name})

        rates = {}

        def absorb(items):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = None
                for k in ("app", "full_name", "name", "service"):
                    if item.get(k):
                        name = str(item[k]).strip().lower()
                        break
                price = None
                for k in ("price", "deduct", "rate", "cost"):
                    if item.get(k) is not None:
                        price = str(item[k])
                        break
                if name and price is not None:
                    rates[name] = price

        if isinstance(data, list):
            absorb(data)
        elif isinstance(data, dict):
            inner = None
            for k in ("rates", "data", "apps", "prices"):
                if isinstance(data.get(k), list):
                    inner = data[k]
                    break
            if inner is not None:
                absorb(inner)
            else:
                # maybe a plain {"AppName": "0.50"} mapping
                for k, v in data.items():
                    if isinstance(v, (str, int, float)):
                        rates[str(k).strip().lower()] = str(v)

        if not rates:
            logger.error(
                "PVAPins get_rates unparsed for '%s'. Raw response: %s",
                country_name,
                data,
            )
            raise Exception(
                f"Could not parse get_rates response for {country_name}."
            )

        return rates

    def purchase(self, service, country, idempotency_key=None):
        payload = {
            "country": str(country).upper(),
            "service": service,
        }
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        data = self._rest("POST", "/orders", json=payload, headers=headers)

        return {
            "success": True,
            "id": str(data.get("id")),
            "order_id": str(data.get("id")),
            "number": data.get("phoneNumber"),
            "phone_number": data.get("phoneNumber"),
            "phone": data.get("phoneNumber"),
            "price_usd": str(data.get("price")),
            "status": data.get("status"),
            "expires_in": data.get("expires_in"),
        }

    def check_sms(self, order_id):
        data = self._rest("GET", f"/orders/{order_id}")

        status = data.get("status")
        otp = data.get("otpCode")

        result = {
            "success": True,
            "status": status,
            "sms": otp,
            "code": otp,
            "otp": otp,
            "full_sms": data.get("message"),
            "message": data.get("message"),
            "phone_number": data.get("phoneNumber"),
            "received": bool(status == "completed" and otp),
            "finished": status in ("expired", "cancelled"),
        }
        return result

    def cancel_order(self, order_id):
        # Classic API needs number + country name + app name (not order id),
        # so we pull them from our own Order record.
        from orders.models import Order

        order = Order.objects.filter(
            provider_order_id=str(order_id)
        ).select_related("country", "service").first()

        if not order:
            raise Exception("Order not found.")

        data = self._classic(
            "get_reject_number.php",
            {
                "number": order.phone_number,
                "country": order.country.name,  # must match PVAPins classic naming
                "app": order.service.name,
            },
        )

        if str(data.get("code")) == "100":
            return {
                "success": True,
                "message": data.get("data", "Number rejected."),
            }

        logger.error("PVAPins reject failed for %s: %s", order_id, data)
        raise Exception(data.get("data") or "Unable to cancel order.")