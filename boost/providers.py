import requests
from django.conf import settings


class GoodLuckBoostHubError(Exception):
    pass


class GoodLuckBoostHub:
    BASE_URL = "https://GoodLuckBoostHub.com/api/v2"

    def __init__(self, api_key=None):
        self.api_key = api_key or settings.RSS_API_KEY
        if not self.api_key:
            raise GoodLuckBoostHubError("RSS_API_KEY is not configured")

    def _request(self, **params):
        params["key"] = self.api_key
        try:
            resp = requests.post(self.BASE_URL, data=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise GoodLuckBoostHubError(f"Connection error: {e}")

        try:
            data = resp.json()
        except ValueError:
            raise GoodLuckBoostHubError("Invalid response from provider")

        # This API returns {"error": "..."} on failure
        if isinstance(data, dict) and data.get("error"):
            raise GoodLuckBoostHubError(data["error"])

        return data

    def get_services(self):
        return self._request(action="services")

    def add_order(self, service_id, link, quantity):
        data = self._request(
            action="add",
            service=service_id,
            link=link,
            quantity=quantity,
        )
        return data["order"]

    def get_orders_status(self, order_ids):
        """order_ids: list of provider order IDs (max 100)"""
        return self._request(action="status", orders=",".join(str(i) for i in order_ids))

    def get_balance(self):
        return self._request(action="balance")