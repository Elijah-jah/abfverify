import json
import logging
from functools import lru_cache

import requests

from django.conf import settings

from .base import BaseProvider

logger = logging.getLogger(__name__)


class SMSBowerProvider(BaseProvider):
    """SMSBower - Server 1 (General, 150+ countries).

    sms-activate compatible API: plain-text responses for actions,
    JSON for listings. Normalized to the same shapes the rest of the
    app already expects (check_sms -> {"status": "finished", ...})."""

    name = "smsbower"
    API_URL = "https://smsbower.page/stubs/handler_api.php"

    WAITING_STATUSES = ("waiting", "pending", "in_progress", None)

    # Where our Country.name differs from SMSBower's english names
    COUNTRY_NAME_ALIASES = {
        "usa": "united states",
        "us": "united states",
        "uk": "united kingdom",
        "uae": "united arab emirates",
        "russia": "russian federation",
        "south korea": "korea",
        "korea": "korea",
        "vietnam": "viet nam",
        "hongkong": "hong kong",
        "czechia": "czech republic",
        "moldova": "moldova, republic of",
        "tanzania": "tanzania",
        "turkey": "turkey",
        "taiwan": "taiwan",
        "venezuela": "venezuela",
        "syria": "syrian arab republic",
        "ivory coast": "cote d`ivoire ivory coast",
        "myanmar": "myanmar",
        "laos": "lao people`s",
    }

    ERROR_MESSAGES = {
        "BAD_KEY": "Invalid provider API key.",
        "BAD_ACTION": "Provider rejected the request type.",
        "BAD_SERVICE": "This service is not available on the provider.",
        "BAD_COUNTRY": "This country is not available on the provider.",
        "NO_ACTIVATION": "Provider could not find this activation.",
        "NO_NUMBERS": "No numbers available right now for this selection.",
        "NO_BALANCE": "Provider balance is too low.",
        "EARLY_CANCEL_DENIED": "Cancellations are only allowed 2+ minutes after purchase.",
        "BAD_STATUS": "Invalid status sent to provider.",
    }

    def __init__(self):
        self.api_key = settings.SMSBOWER_API_KEY

    # ------------------------------------------------------------------
    # Request core
    # ------------------------------------------------------------------

    def _request(self, action, **params):
        """GET to handler_api.php. Returns parsed JSON for JSON actions,
        raw text for plain-text actions."""
        payload = {"api_key": self.api_key, "action": action}
        for k, v in params.items():
            if v is not None:
                payload[k] = str(v)

        try:
            response = requests.get(self.API_URL, params=payload, timeout=15)
            response.raise_for_status()
        except requests.Timeout:
            logger.error("SMSBower timeout: action=%s", action)
            raise Exception("Provider is taking too long. Please try again.")
        except requests.ConnectionError:
            logger.error("SMSBower connection error: action=%s", action)
            raise Exception("Unable to connect to provider. Please try again.")
        except requests.HTTPError as e:
            logger.error("SMSBower HTTP error: action=%s status=%s",
                         action, e.response.status_code)
            raise Exception("Provider returned an error. Please try again.")
        except requests.RequestException:
            logger.exception("SMSBower request failed: action=%s", action)
            raise Exception("Provider request failed. Please try again.")

        text = response.text.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return text

    def _fail(self, response):
        if isinstance(response, str):
            raise Exception(self.ERROR_MESSAGES.get(response,
                                                    f"Provider error: {response}"))
        raise Exception(f"Unexpected provider response: {response!r}")

    # ------------------------------------------------------------------
    # Country name -> SMSBower numeric id
    # ------------------------------------------------------------------

    @lru_cache(maxsize=1)
    def _country_map(self):
        """{lowercase english name: numeric id} built from getCountries.
        Handles all response shapes: list of dicts, dict keyed by id,
        or wrapped in an outer key."""
        res = self.get_countries()

        # Unwrap one level if needed: {"countries": [...]} or similar
        if isinstance(res, dict) and not any(
            isinstance(v, dict) and ("eng" in v or "rus" in v) for v in res.values()
        ):
            for v in res.values():
                if isinstance(v, (list, dict)):
                    res = v
                    break

        mapping = {}
        if isinstance(res, list):
            # Shape: [{"id": 1003, "eng": "Bermuda", ...}, ...]
            for item in res:
                if not isinstance(item, dict):
                    continue
                eng = (item.get("eng") or "").strip().lower()
                cid = str(item.get("id", "")).strip()
                if eng and cid.isdigit():
                    mapping[eng] = int(cid)
        elif isinstance(res, dict):
            # Shape: {"0": {"eng": "Russian Federation", ...}, ...}
            for cid, names in res.items():
                if not isinstance(names, dict):
                    continue
                eng = (names.get("eng") or "").strip().lower()
                cid = str(cid).strip()
                if eng and cid.isdigit():
                    mapping[eng] = int(cid)
        return mapping
    
    def resolve_country_id(self, name_or_id):
        """Accept an already-numeric id, or map a country name to SMSBower's id."""
        s = str(name_or_id or "").strip()
        if s.isdigit():
            return s
        key = self.COUNTRY_NAME_ALIASES.get(s.lower(), s.lower())
        country_id = self._country_map().get(key)
        if country_id is None:
            raise Exception(f"Country not available on SMSBower: {name_or_id}")
        return str(country_id)

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def get_balance(self):
        res = self._request("getBalance")
        if isinstance(res, str) and res.startswith("ACCESS_BALANCE:"):
            return float(res.split(":", 1)[1])
        self._fail(res)

    def get_countries(self):
        return self._request("getCountries")

    def get_services(self, country=None):
        res = self._request("getServicesList")
        if isinstance(res, dict) and res.get("status") == "success":
            return res["services"]
        self._fail(res)

    def get_price(self, service, country):
        cid = self.resolve_country_id(country)
        res = self._request("getPrices", service=service, country=cid)
        try:
            info = res[cid][service]
            return {"success": True, "cost": info["cost"], "count": info["count"]}
        except (KeyError, TypeError):
            raise Exception("Price not available for this service/country.")

    def check_stock(self, service, country):
        info = self.get_price(service, country)
        return {"success": True, "count": info["count"]}

    def purchase(self, service, country, max_price=None):
        """getNumberV2 — returns the same shape views already use:
        result["order_id"], result["phone_number"]."""
        cid = self.resolve_country_id(country)
        res = self._request("getNumberV2", service=service, country=cid,
                            maxPrice=max_price)
        if isinstance(res, dict) and "activationId" in res:
            return {
                "success": True,
                "order_id": str(res["activationId"]),
                "phone_number": str(res["phoneNumber"]),
                "cost": res.get("activationCost"),
                "operator": res.get("activationOperator"),
            }
        self._fail(res)

    def check_sms(self, order_id):
        """Normalized: {"status": "finished", "sms": code} or waiting/cancelled."""
        res = self._request("getStatus", id=order_id)
        if not isinstance(res, str):
            self._fail(res)
        if res.startswith("STATUS_OK:"):
            code = res.split(":", 1)[1].strip().strip("'")
            return {"status": "finished", "sms": code, "full_sms": ""}
        if res in ("STATUS_WAIT_CODE",) or res.startswith("STATUS_WAIT_RETRY:"):
            return {"status": "waiting", "sms": "", "full_sms": ""}
        if res == "STATUS_CANCEL":
            return {"status": "cancelled", "sms": "", "full_sms": ""}
        self._fail(res)

    def cancel(self, order_id):
        """setStatus status=8. Provider rejects cancels inside 2 minutes."""
        res = self._request("setStatus", status=8, id=order_id)
        if res in ("ACCESS_CANCEL", "ACCESS_ACTIVATION", "ACCESS_READY"):
            return {"success": True}
        self._fail(res)

    def get_all_prices(self, country):
        """{service_code: {"cost": usd, "count": stock}} — feeds sync commands."""
        cid = self.resolve_country_id(country)
        res = self._request("getPrices", country=cid)
        out = {}
        for services in (res or {}).values():
            for svc, info in (services or {}).items():
                out[str(svc).strip().lower()] = {
                    "cost": info.get("cost", 0),
                    "count": info.get("count", 0),
                }
        return out