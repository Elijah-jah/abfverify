"""DaisySMS provider - sms-activate compatible API.

Docs: https://daisysms.io/docs/api
"""

import json
import logging
import os
import time

import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)

BASE_URL = "https://daisysms.io/stubs/handler_api.php"
COUNTRY_USA = 187  # USA code in sms-activate compatible API

MAX_RETRIES = 3   # total attempts per request
RETRY_WAIT = 2    # seconds between attempts

# Browser-like User-Agent - the default "python-requests/x.y" UA is
# blocked by Cloudflare / the origin WAF (returns 403 Forbidden).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

# Raw provider errors -> friendly messages
ERRORS = {
    "BAD_KEY": "Invalid DaisySMS API key",
    "NO_NUMBERS": "No numbers available for this service right now",
    "NO_MONEY": "Insufficient DaisySMS balance - top up your account",
    "MAX_PRICE_EXCEEDED": "Current price is above the allowed max_price",
    "TOO_MANY_ACTIVE_RENTALS": (
        "Account limit reached (20 active rentals). "
        "Finish or cancel existing orders first"
    ),
    "NO_ACTIVATION": "Order/rental not found",
    "ACCESS_READY": "Rental already completed",
}


class DaisySMSError(Exception):
    """Raised when DaisySMS returns a business-logic error."""


def _friendly_error(raw: str) -> str:
    return ERRORS.get(raw.strip(), raw.strip())


class DaisySMSProvider:
    def __init__(self, api_key: str = None):
        # Key can be passed explicitly, otherwise read from the environment.
        # Set DAISYSMS_API_KEY in your Render dashboard / .env file.
        self.api_key = api_key or os.environ.get("DAISYSMS_API_KEY")
        if not self.api_key:
            raise DaisySMSError(
                "No DaisySMS API key provided. Set the DAISYSMS_API_KEY "
                "environment variable or pass api_key= explicitly."
            )

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------

    def _request(self, params: dict) -> requests.Response:
        """GET the API with retries on transient network failures."""
        params = {**params, "api_key": self.api_key}

        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(
                    BASE_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=30,
                )
                response.raise_for_status()
                if response.text.strip() == "BAD_KEY":
                    raise PermissionError("DaisySMS rejected the API key (BAD_KEY)")
                return response
            except (ConnectionError, Timeout) as e:
                last_exc = e
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "DaisySMS attempt %d/%d failed (%s). Retrying in %ds...",
                        attempt, MAX_RETRIES, type(e).__name__, RETRY_WAIT,
                    )
                    time.sleep(RETRY_WAIT)

        raise last_exc

    def _get_price_map(self, country: int = COUNTRY_USA) -> dict:
        """Return {service_code: {cost, count}} for a country."""
        data = json.loads(
            self._request({"action": "getPrices", "country": country}).text
        )
        if not isinstance(data, dict):
            return {}

        # Shape A: {service: {cost, count}}
        sample = next(iter(data.values()), None)
        if isinstance(sample, dict) and ("cost" in sample or "count" in sample):
            return data

        # Shape B: {country: {service: {cost, count}}}
        inner = data.get(str(country)) or data.get(country) or {}
        return inner if isinstance(inner, dict) else {}

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def check_balance(self) -> float:
        """Balance in dollars."""
        result = self._request({"action": "getBalance"}).text
        if result.startswith("ACCESS_BALANCE:"):
            return float(result.split(":")[1])
        raise DaisySMSError(f"Unexpected balance response: {result}")

    # ------------------------------------------------------------------
    # Catalog / prices / stock
    # ------------------------------------------------------------------

    def get_services(self) -> list:
        """All services available for USA: [{"code": ..., "name": ...}, ...]"""
        try:
            data = self._get_price_map(COUNTRY_USA)
            services = [
                {"code": code, "name": code.replace("_", " ").title()}
                for code in data
            ]
            if services:
                return services
        except Exception as e:
            logger.error("Failed to fetch DaisySMS services: %s", e)
        return []

    def check_stock(self, service: str, country: int = COUNTRY_USA,
                    max_price=None) -> dict:
        """{"available": count, "price": cost} - count capped at 100 by Daisy."""
        try:
            info = self._get_price_map(country).get(service)
            if info:
                return {
                    "available": int(info.get("count", 0)),
                    "price": float(info.get("cost", 0) or 0),
                }
            return {"available": 0, "price": 0}
        except Exception as e:
            logger.error("Failed to check DaisySMS stock: %s", e)
            return {"available": 0, "error": "Unable to check stock"}

    def get_price(self, service: str, country: int = COUNTRY_USA) -> dict:
        """{"success": bool, "price_usd": float}"""
        try:
            cost = self._get_price_map(country).get(service, {}).get("cost", 0)
            if cost:
                return {"success": True, "price_usd": float(cost)}
        except Exception as e:
            logger.error("Failed to get DaisySMS price: %s", e)
        return {"success": False, "price_usd": 0}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def purchase(self, service: str, country: int = COUNTRY_USA,
                 max_price=None, areas=None, carriers=None) -> dict:
        """
        Rent a number.
        Returns: {"order_id", "phone_number", "status": "waiting", "price_usd"}
        Raises DaisySMSError with a friendly message on NO_NUMBERS / NO_MONEY etc.
        """
        params = {"action": "getNumber", "service": service, "country": country}
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
                "price_usd": (
                    float(response.headers["X-Price"])
                    if response.headers.get("X-Price")
                    else None
                ),
            }

        raise DaisySMSError(f"DaisySMS purchase failed: {_friendly_error(result)}")

    def check_sms(self, order_id: str, full_text: bool = True) -> dict:
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
        if result == "STATUS_WAIT_CODE":
            return {"status": "waiting"}
        if result == "STATUS_CANCEL":
            return {"status": "cancelled"}
        if result == "NO_ACTIVATION":
            return {"status": "error", "message": "Invalid order ID"}
        return {"status": "waiting"}

    def cancel_order(self, order_id: str) -> dict:
        """Cancel rental, refund to balance."""
        result = self._request({
            "action": "setStatus", "id": order_id, "status": 8,
        }).text

        if result == "ACCESS_CANCEL":
            return {"success": True}
        return {"success": False, "error": _friendly_error(result)}

    def mark_done(self, order_id: str) -> bool:
        """Mark rental done (frees up your 20-active-rental slot)."""
        result = self._request({
            "action": "setStatus", "id": order_id, "status": 6,
        }).text
        return result == "ACCESS_ACTIVATION"