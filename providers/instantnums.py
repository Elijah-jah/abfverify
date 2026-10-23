import logging
import re

import requests

from django.conf import settings

from .base import BaseProvider

logger = logging.getLogger(__name__)


class InstantNumsProvider(BaseProvider):
    """InstantNums — Server 1 (General, 150+ countries)."""

    name = "instantnums"

    # Key names that might carry the OTP code
    CODE_KEYS = (
        "code", "sms_code", "otp", "pin", "verification_code",
        "security_code", "auth_code", "passcode",
    )
    # Key names that might carry the full SMS text
    TEXT_KEYS = ("full_sms", "sms", "text", "body", "content", "msg", "fulltext", "message")
    # Provider statuses that simply mean "no SMS yet"
    WAITING_MARKERS = ("waiting", "pending", "in_progress", "STATUS_WAIT_CODE", "STATUS_WAIT_RETRY", None)

    def __init__(self):
        self.base_url = settings.INSTANTNUMS_BASE_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.INSTANTNUMS_API_KEY}",
            "Accept": "application/json",
        }

    def _make_request(self, method, endpoint, **kwargs):
        """Centralized request handler with logging and error handling."""
        url = f"{self.base_url}{endpoint}"
        timeout = kwargs.pop("timeout", 10)

        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

        except requests.Timeout:
            logger.error("InstantNums timeout: %s %s", method, url)
            raise Exception("Provider is taking too long. Please try again.")

        except requests.ConnectionError:
            logger.error("InstantNums connection error: %s %s", method, url)
            raise Exception("Unable to connect to provider. Please try again.")

        except requests.HTTPError as e:
            try:
                detail = e.response.json().get("message")
            except (ValueError, AttributeError):
                detail = None
            msg = detail or "Provider returned an error. Please try again."
            logger.error(
                "InstantNums HTTP error: %s %s - Status: %s - %s",
                method, url, e.response.status_code, msg,
            )
            raise Exception(msg)

        except requests.RequestException:
            logger.exception("InstantNums request failed: %s %s", method, url)
            raise Exception("Provider request failed. Please try again.")
        except ValueError:
            # response.json() failed — non-JSON body. Log it so we can see the real shape.
            logger.error("InstantNums returned non-JSON: %s", response.text[:500])
            return {"raw": response.text}

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def get_balance(self):
        return self._make_request("GET", "/balance")

    def get_countries(self):
        return self._make_request("GET", "/countries")

    def get_services(self, country=None):
        params = {"country": country} if country else None
        return self._make_request("GET", "/services", params=params)

    def get_price(self, service, country):
        data = self._make_request(
            "GET",
            "/price",
            params={"service": service, "country": country},
        )
        if not data.get("success"):
            logger.error("InstantNums price fetch failed: %s", data)
            raise Exception(data.get("message", "Unable to fetch price from InstantNums."))
        return data

    def check_stock(self, service, country):
        data = self._make_request(
            "GET",
            "/stock",
            params={"service": service, "country": country},
        )
        if not data.get("success"):
            logger.error("InstantNums stock check failed: %s", data)
            raise Exception(data.get("message", "Unable to check stock from InstantNums."))
        return data

    def purchase(self, service, country):
        data = self._make_request(
            "POST",
            "/sms/purchase",
            json={
                "service": str(service),
                "country": str(country),
            },
        )
        if not data.get("success"):
            logger.error("InstantNums purchase failed: %s", data)
            raise Exception(data.get("message", "Unable to purchase a number from InstantNums."))
        return data

    # ------------------------------------------------------------------
    # SMS checking — hardened to handle ANY response shape
    # ------------------------------------------------------------------

    def check_sms(self, order_id):
        data = self._make_request("GET", f"/sms/{order_id}")

        # ALWAYS log the raw response — this is how we learn the real shape
        logger.info("InstantNums check_sms RAW for %s: %s", order_id, data)

        return self._normalize_sms(data, order_id)

    def _normalize_sms(self, data, order_id):
        """Turn whatever InstantNums returns into the standard shape:
        {"status": "finished", "sms": "12345", "full_sms": "..."}
        or {"status": "waiting"} while no SMS has arrived.
        """
        if isinstance(data, str):
            data = {"raw": data}
        if not isinstance(data, dict):
            return {"status": "waiting", "sms": "", "full_sms": ""}

        # Unwrap nested payloads: {"data": {...}} or {"result": {...}}
        payload = data
        for wrapper in ("data", "result", "response"):
            inner = payload.get(wrapper)
            if isinstance(inner, dict):
                payload = inner

        # --- Case A: sms-activate style plain-text status ---
        for key in ("raw", "status", "result"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith("STATUS_"):
                if value.startswith("STATUS_OK:"):
                    return {
                        "status": "finished",
                        "sms": value.split(":", 1)[1],
                        "full_sms": "",
                    }
                if value in ("STATUS_WAIT_CODE", "STATUS_WAIT_RETRY"):
                    return {"status": "waiting", "sms": "", "full_sms": ""}
                if value == "STATUS_CANCEL":
                    return {"status": "cancelled", "sms": "", "full_sms": ""}
                if value == "NO_ACTIVATION":
                    logger.warning("InstantNums: order %s not found (%s)", order_id, value)
                    return {"status": "waiting", "sms": "", "full_sms": ""}

        # --- Case B: code under a known key (including inside message text) ---
        code = None
        for key in self.CODE_KEYS:
            value = payload.get(key)
            if value not in (None, "", 0, "0"):
                code = str(value).strip()
                if code:
                    break

        # Fallback: pull a 4-8 digit code out of any text field
        full_sms = ""
        if not code:
            for key in self.TEXT_KEYS:
                value = payload.get(key)
                if isinstance(value, str) and value:
                    if not full_sms:
                        full_sms = value
                    match = re.search(r"\b(\d{4,8})\b", value)
                    if match:
                        code = match.group(1)
                        break
        else:
            for key in self.TEXT_KEYS:
                value = payload.get(key)
                if isinstance(value, str) and value:
                    full_sms = value
                    break

        if code:
            result = {"status": "finished", "sms": code, "full_sms": full_sms or ""}
            logger.info("InstantNums code FOUND for %s: %s", order_id, result)
            return result

        # Explicit waiting states or nothing useful — treat as waiting
        logger.info("InstantNums no code yet for %s (payload keys: %s)", order_id, list(payload.keys()))
        return {"status": "waiting", "sms": "", "full_sms": ""}

    def cancel(self, order_id):
        data = self._make_request("POST", f"/sms/{order_id}/cancel")

        # Tolerant: only fail on an EXPLICIT error signal.
        # Some APIs return {"status": "ok"} or no flag at all on success.
        if isinstance(data, dict):
            if data.get("success") is False:
                logger.error("InstantNums cancel failed for order %s: %s", order_id, data)
                raise Exception(data.get("message", "Unable to cancel order from InstantNums."))
            if data.get("error"):
                logger.error("InstantNums cancel error for order %s: %s", order_id, data)
                raise Exception(str(data.get("error")))
            if data.get("status") in ("error", "failed"):
                logger.error("InstantNums cancel failed for order %s: %s", order_id, data)
                raise Exception(data.get("message", "Unable to cancel order from InstantNums."))

        # success=True, or no explicit error flag — treat as cancelled
        logger.info("InstantNums cancel accepted for order %s: %s", order_id, data)
        return data

    def get_all_prices(self, country):
        """
        Fetch all service prices for one country in one call.
        Handles list or dict response shapes; raises if the API
        requires a service param (i.e. bulk not supported).
        """
        data = self._make_request(
            "GET",
            "/price",
            params={"country": str(country)},
        )
        if not data.get("success"):
            raise Exception(data.get("message", "Price fetch failed"))

        prices = data.get("prices")

        # Shape A: {"prices": [{"service": "wa", "price_usd": 1.6, "available": 100}, ...]}
        if isinstance(prices, list):
            return {
                str(p["service"]).strip().lower(): {
                    "cost": p.get("price_usd", 0),
                    "count": p.get("available", 0),
                }
                for p in prices if p.get("service")
            }

        # Shape B: {"prices": {"wa": 1.6, ...}}
        if isinstance(prices, dict):
            return {
                str(k).strip().lower(): {"cost": v, "count": 0}
                for k, v in prices.items()
            }

        raise Exception("Bulk prices not supported (single-pair response)")
