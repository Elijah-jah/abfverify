"""DaisySMS provider - sms-activate compatible API.

Allowed API actions ONLY:
  - getNumber      (purchase number)
  - getStatus      (poll SMS)
  - setStatus      (cancel / mark done)
  - getPrices      (bulk price sync — used ONLY by `update_prices` command)

Prices for users are served from the local database (Pricing model).
No live price/balance/service requests happen during normal site usage.
"""

import json
import logging

import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)

BASE_URL = "https://daisysms.io/stubs/handler_api.php"
COUNTRY_USA = 187  # USA code in sms-activate compatible API

# NOTE: "br" (brotli) is intentionally excluded — requests cannot decode it
# without the brotli package, and an undecoded body breaks error detection.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://daisysms.io/",
}

# Raw provider errors -> friendly messages
ERRORS = {
    "BAD_KEY": "Invalid DaisySMS API key",
    "WRONG_API_KEY": "Invalid DaisySMS API key",
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

# Errors that should NOT trigger a retry (permanent failures)
NON_RETRYABLE = {"BAD_KEY", "WRONG_API_KEY", "NO_MONEY", "TOO_MANY_ACTIVE_RENTALS"}


class DaisySMSError(Exception):
    """Raised when DaisySMS returns a business-logic error."""

    def __init__(self, message: str, raw: str = "", retryable: bool = False):
        super().__init__(message)
        self.raw = raw
        self.retryable = retryable


def _friendly_error(raw: str) -> str:
    return ERRORS.get(raw.strip(), raw.strip())


def _is_cloudflare_challenge(text: str) -> bool:
    """Detect Cloudflare 'Just a moment...' interstitial pages."""
    return (
        "<title>Just a moment" in text
        or "challenges.cloudflare.com" in text
        or "cf-mitigated" in text.lower()
    )


class DaisySMSProvider:
    """DaisySMS API client.

    Only purchase / poll / cancel / bulk-price-sync methods remain.
    Keeps a persistent requests.Session so Cloudflare sees consistent
    cookies/headers across calls from the same process.
    """

    def __init__(self, api_key: str, proxy: str | None = None):
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(BROWSER_HEADERS)
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------

    def _request(self, params: dict) -> requests.Response:
        """GET the DaisySMS API — single attempt, no retries.

        Raises PermissionError on auth failures and DaisySMSError on
        Cloudflare blocks / business errors.
        """
        params = dict(params)
        params["api_key"] = self.api_key

        try:
            response = self._session.get(BASE_URL, params=params, timeout=30)
        except (ConnectionError, Timeout) as e:
            raise DaisySMSError(
                f"Could not reach DaisySMS ({type(e).__name__})"
            ) from e

        logger.info(
            "DaisySMS %s: status=%s body=%s",
            params.get("action"),
            response.status_code,
            response.text[:500],
        )

        # --- Hard auth failures ---
        if response.status_code == 401:
            raise PermissionError(
                "DaisySMS rejected the API key (401). "
                "Check your DaisySMS dashboard key."
            )

        body = response.text.strip()

        if body in ("BAD_KEY", "WRONG_API_KEY"):
            raise PermissionError("DaisySMS rejected the API key (BAD_KEY)")

        if body in NON_RETRYABLE:
            raise DaisySMSError(
                f"DaisySMS error: {_friendly_error(body)}",
                raw=body,
            )

        # --- Cloudflare block: fail fast with a clear message ---
        if response.status_code == 403:
            if _is_cloudflare_challenge(response.text):
                raise DaisySMSError(
                    "DaisySMS blocked by Cloudflare (403). "
                    "Contact DaisySMS support to whitelist your server IP."
                )
            raise DaisySMSError(
                f"403 Forbidden from DaisySMS: {response.text[:200]}"
            )

        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # Price sync — used ONLY by `py manage.py update_prices`
    # Never called during normal site traffic.
    # ------------------------------------------------------------------

    def get_all_prices(self, country: int = COUNTRY_USA) -> dict:
        """
        One-shot price map: {"service_code": {"cost": float, "count": int}}.
        """
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
        Poll for the SMS code.
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