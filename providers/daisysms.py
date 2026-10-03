"""DaisySMS provider - sms-activate compatible API.

Docs: https://daisysms.io/docs/api
Rebuilt with: session persistence, exponential backoff + jitter,
Cloudflare 403 detection/retry, and request rate limiting.
"""

import json
import logging
import random
import time

import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

logger = logging.getLogger(__name__)

BASE_URL = "https://daisysms.io/stubs/handler_api.php"
COUNTRY_USA = 187  # USA code in sms-activate compatible API

MAX_RETRIES = 4            # total attempts per request
BASE_RETRY_WAIT = 2        # base seconds for exponential backoff
JITTER_RANGE = (0, 1.5)    # random extra seconds to avoid thundering herd
MIN_REQUEST_INTERVAL = 1.0  # min seconds between API calls (rate limit courtesy)

# Realistic browser headers — datacenter requests with default python-requests
# headers are the #1 thing Cloudflare's bot score flags.
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


def _is_non_retryable(text: str) -> bool:
    """True if the body is a known permanent-failure error code."""
    return text.strip() in NON_RETRYABLE


class DaisySMSProvider:
    """DaisySMS API client.

    Keeps a persistent requests.Session so Cloudflare sees consistent
    cookies/headers across calls from the same process.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(BROWSER_HEADERS)
        self._last_request_at = 0.0

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------

    def _wait_for_rate_limit(self):
        """Enforce a minimum gap between requests."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    def _request(self, params: dict) -> requests.Response:
        """GET the DaisySMS API with exponential backoff + jitter.

        Retries on: connection errors, timeouts, HTTP 5xx, and 403
        Cloudflare challenges (intermittent per-IP).
        Does NOT retry: permanent business errors (BAD_KEY, NO_MONEY, etc.)
        """
        params = dict(params)
        params["api_key"] = self.api_key

        last_exc = None

        for attempt in range(1, MAX_RETRIES + 1):
            self._wait_for_rate_limit()

            try:
                response = self._session.get(
                    BASE_URL,
                    params=params,
                    timeout=30,
                )

                logger.info(
                    "DaisySMS %s: status=%s body=%s",
                    params.get("action"),
                    response.status_code,
                    response.text[:500],
                )

                # --- Hard auth failures: never retry ---
                if response.status_code == 401:
                    raise PermissionError(
                        "DaisySMS rejected the API key (401). "
                        "Check your DaisySMS dashboard key."
                    )

                body = response.text.strip()

                if body in ("BAD_KEY", "WRONG_API_KEY"):
                    raise PermissionError(
                        "DaisySMS rejected the API key (BAD_KEY)"
                    )

                if _is_non_retryable(body):
                    raise DaisySMSError(
                        f"DaisySMS error: {_friendly_error(body)}",
                        raw=body,
                        retryable=False,
                    )

                # --- Cloudflare 403 challenge: retry with backoff ---
                if response.status_code == 403:
                    if _is_cloudflare_challenge(response.text):
                        last_exc = DaisySMSError(
                            "DaisySMS blocked by Cloudflare (403). "
                            "Contact DaisySMS support to whitelist your "
                            "server IP.",
                            retryable=True,
                        )
                    else:
                        last_exc = HTTPError(
                            f"403 Forbidden from DaisySMS: {response.text[:200]}"
                        )

                    if attempt < MAX_RETRIES:
                        wait = BASE_RETRY_WAIT * (2 ** (attempt - 1)) + random.uniform(*JITTER_RANGE)
                        logger.warning(
                            "DaisySMS %s attempt %d/%d blocked (403). "
                            "Retrying in %.1fs...",
                            params.get("action"), attempt, MAX_RETRIES, wait,
                        )
                        time.sleep(wait)
                        continue

                    raise last_exc

                response.raise_for_status()
                return response

            except (ConnectionError, Timeout) as e:
                last_exc = e

                if attempt < MAX_RETRIES:
                    wait = BASE_RETRY_WAIT * (2 ** (attempt - 1)) + random.uniform(*JITTER_RANGE)
                    logger.warning(
                        "DaisySMS %s attempt %d/%d failed (%s). "
                        "Retrying in %.1fs...",
                        params.get("action"), attempt, MAX_RETRIES,
                        type(e).__name__, wait,
                    )
                    time.sleep(wait)

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
    # Catalog / prices
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

    def get_price(self, service: str, country: int = COUNTRY_USA) -> dict:
        """{"success": bool, "price_usd": float}"""
        try:
            cost = self._get_price_map(country).get(service, {}).get("cost", 0)
            if cost:
                return {"success": True, "price_usd": float(cost)}
        except Exception as e:
            logger.error("Failed to get DaisySMS price: %s", e)
        return {"success": False, "price_usd": 0}

    def get_all_prices(self, country: int = COUNTRY_USA) -> dict:
        """
        One-shot price map: {"service_code": {"cost": float, "count": int}}.
        Use this for bulk updates instead of calling get_price() per service.
        """
        return self._get_price_map(country)

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