import logging
import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class InstantNumsProvider:

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
            logger.error("InstantNums HTTP error: %s %s - Status: %s", method, url, e.response.status_code)
            raise Exception("Provider returned an error. Please try again.")

        except requests.RequestException:
            logger.exception("InstantNums request failed: %s %s", method, url)
            raise Exception("Provider request failed. Please try again.")

    def get_balance(self):
        response = self._make_request(
            "GET",
            "/balance",
        )
        return response

    def get_countries(self):
        response = self._make_request(
            "GET",
            "/countries",
        )
        return response

    def get_services(self):
        response = self._make_request(
            "GET",
            "/services",
        )
        return response

    def get_price(self, service, country):
        data = self._make_request(
            "GET",
            "/price",
            params={
                "service": service,
                "country": country,
            },
        )

        if not data.get("success"):
            logger.error("InstantNums price fetch failed: %s", data)
            raise Exception("Unable to fetch price from InstantNums.")

        return data

    def check_stock(self, service, country):
        """
        Check whether numbers are available for
        the selected service and country.
        """

        data = self._make_request(
            "GET",
            "/stock",
            params={
                "service": service,
                "country": country,
            },
        )

        if not data.get("success"):
            logger.error("InstantNums stock check failed: %s", data)
            raise Exception("Unable to check stock from InstantNums.")

        return data

    def purchase(self, service, country):
        """
        Purchase a virtual number from InstantNums.
        """

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
            raise Exception("Unable to purchase a number from InstantNums.")

        return data

    def check_sms(self, order_id):
        data = self._make_request(
            "GET",
            f"/sms/{order_id}",
        )

        if not data.get("success"):
            logger.error("InstantNums SMS check failed for order %s: %s", order_id, data)
            raise Exception("Unable to retrieve SMS from InstantNums.")

        return data

    def cancel_order(self, order_id):
        data = self._make_request(
            "POST",
            f"/sms/{order_id}/cancel",
        )

        if not data.get("success"):
            logger.error("InstantNums cancel failed for order %s: %s", order_id, data)
            raise Exception(
                data.get(
                    "message",
                    "Unable to cancel order from InstantNums."
                )
            )

        return data