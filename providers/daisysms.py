import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://daisysms.io/stubs/handler_api.php"
COUNTRY_USA = 187  # USA code in sms-activate compatible API

# Raw provider errors -> friendly messages
ERRORS = {
    "BAD_KEY": "Invalid DaisySMS API key",
    "NO_NUMBERS": "No numbers available for this service right now",
    "NO_MONEY": "Insufficient DaisySMS balance - top up your account",
    "MAX_PRICE_EXCEEDED": "Current price is above the allowed max_price",
    "TOO_MANY_ACTIVE_RENTALS": "Account limit reached (20 active rentals). Finish or cancel existing orders first",
    "NO_ACTIVATION": "Order/rental not found",
    "ACCESS_READY": "Rental already completed",
}


class DaisySMSProvider:
    """DaisySMS provider - sms-activate compatible API.

    Docs: https://daisysms.io/docs/api
    Set DAISYSMS_PROXY env var (http://user:pass@ip:port) to route
    requests through a proxy - needed if your server IP is blocked (403).
    """

    def __init__(self, api_key):
        self.api_key = api_key
        proxy = os.environ.get("DAISYSMS_PROXY", "").strip()
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------

    def _request(self, params):
        """GET the API. Returns the raw response object (headers included)."""
        params = dict(params)
        params["api_key"] = self.api_key
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30,
            proxies=self.proxies,
        )
        response.raise_for_status()
        if response.text.strip() == "BAD_KEY":
            raise PermissionError("DaisySMS rejected the API key (BAD_KEY)")
        return response

    def _get_price_map(self, country=COUNTRY_USA):
        """Return {service_code: {cost, count}} for a country."""
        data = json.loads(
            self._request({"action": "getPrices", "country": country}).text
        )
        if not isinstance(data, dict):
            return {}

        # Shape A: {service: {cost, count}} (what getPrices returns with country param)
        sample = next(iter(data.values()), None)
        if isinstance(sample, dict) and ("cost" in sample or "count" in sample):
            return data

        # Shape B: {country: {service: {cost, count}}}
        inner = data.get(str(country)) or data.get(country) or {}
        return inner if isinstance(inner, dict) else {}

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def check_balance(self):
        """Balance in dollars."""
        result = self._request({"action": "getBalance"}).text
        if result.startswith("ACCESS_BALANCE:"):
            return float(result.split(":")[1])
        raise Exception(f"Unexpected balance response: {result}")

    # ------------------------------------------------------------------
    # Catalog / prices / stock
    # ------------------------------------------------------------------

    def get_services(self):
        """All services available for USA: [{"code": "whatsapp", "name": "Whatsapp"}, ...]"""
        try:
            data = self._get_price_map(COUNTRY_USA)
            services = [
                {"code": code, "name": code.replace("_", " ").title()}
                for code in data
            ]
            if services:
                return services
        except Exception as e:
            logger.error(f"Failed to fetch DaisySMS services: {e}")
        return []

    def check_stock(self, service, country=COUNTRY_USA, max_price=None):
        """{"available": count, "price": cost} - count is capped at 100 by Daisy."""
        try:
            info = self._get_price_map(country).get(service)
            if info:
                return {
                    "available": int(info.get("count", 0)),
                    "price": float(info.get("cost", 0) or 0),
                }
            return {"available": 0, "price": 0}
        except Exception as e:
            logger.error(f"Failed to check DaisySMS stock: {e}")
            return {"available": 0, "error": "Unable to check stock"}

    def get_price(self, service, country=COUNTRY_USA):
        """{"success": bool, "price_usd": float}"""
        try:
            cost = self._get_price_map(country).get(service, {}).get("cost", 0)
            if cost:
                return {"success": True, "price_usd": float(cost)}
        except Exception as e:
            logger.error(f"Failed to get DaisySMS price: {e}")
        return {"success": False, "price_usd": 0}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def purchase(self, service, country=COUNTRY_USA, max_price=None, areas=None, carriers=None):
        """
        Rent a number.
        Returns: {"order_id", "phone_number", "status": "waiting", "price_usd"}
        Raises Exception with a friendly message on NO_NUMBERS / NO_MONEY / etc.
        """
        params = {
            "action": "getNumber",
            "service": service,
            "country": country,
        }
        if max_price:
            params["max_price"] = max_price
        if areas:
            params["areas"] = areas
        if carriers:
            params["carriers"] = carriers

        response = self._request(params)
        result = response.text

        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            return {
                "order_id": parts[1],
                "phone_number": parts[2],
                "status": "waiting",
                "price_usd": float(response.headers["X-Price"])
                if response.headers.get("X-Price")
                else None,
            }

        raise Exception(f"DaisySMS purchase failed: {ERRORS.get(result.strip(), result.strip())}")

    def check_sms(self, order_id, full_text=True):
        """
        Poll for the SMS code (every 3s+ recommended by Daisy).
        full_text=True also returns the entire message via the X-Text header.
        """
        params = {"action": "getStatus", "id": order_id}
        if full_text:
            params["text"] = 1

        response = self._request(params)
        result = response.text

        if result.startswith("STATUS_OK:"):
            return {
                "status": "finished",
                "sms": result.split(":", 1)[1],
                "full_sms": response.headers.get("X-Text"),
            }
        elif result == "STATUS_WAIT_CODE":
            return {"status": "waiting"}
        elif result == "STATUS_CANCEL":
            return {"status": "cancelled"}
        elif result == "NO_ACTIVATION":
            return {"status": "error", "message": "Invalid order ID"}
        else:
            return {"status": "waiting"}

    def cancel_order(self, order_id):
        """Cancel rental, refund to balance."""
        result = self._request({
            "action": "setStatus",
            "id": order_id,
            "status": 8,
        }).text

        if result == "ACCESS_CANCEL":
            return {"success": True}
        return {"success": False, "error": ERRORS.get(result.strip(), result.strip())}

    def mark_done(self, order_id):
        """Mark rental done (frees up your 20-active-rental slot)."""
        result = self._request({
            "action": "setStatus",
            "id": order_id,
            "status": 6,
        }).text
        return result == "ACCESS_ACTIVATION"