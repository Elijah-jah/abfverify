import requests
import logging
import json

logger = logging.getLogger(__name__)

BASE_URL = "https://daisysms.io/stubs/handler_api.php"


class DaisySMSProvider:
    def __init__(self, api_key):
        self.api_key = api_key

    def _request(self, params):
        """Make request to DaisySMS API."""
        params["api_key"] = self.api_key
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.text

    def check_balance(self):
        """Get account balance in dollars."""
        result = self._request({"action": "getBalance"})
        if result.startswith("ACCESS_BALANCE:"):
            return float(result.split(":")[1])
        return 0.0

    def get_services(self):
        """
        Fetch all available services from DaisySMS.
        Returns: [{"code": "amazon", "name": "Amazon"}, ...]
        """
        try:
            result = self._request({"action": "getPrices", "country": 187})
            data = json.loads(result)
            
            services = []
            if isinstance(data, dict):
                for code, info in data.items():
                    # Convert code to title case for name
                    name = code.replace("_", " ").title()
                    services.append({"code": code, "name": name})
                    
            if services:
                return services
                
        except Exception as e:
            logger.error(f"Failed to fetch DaisySMS services: {e}")
            
        return []

    def check_stock(self, service, country=187, max_price=None):
        """
        Check stock using getPrices.
        Returns: {"available": count, "price": cost}
        """
        try:
            params = {
                "action": "getPrices",
                "country": country,
            }
            
            result = self._request(params)
            data = json.loads(result)
            
            # Format: {"amazon": {"cost": 0.3, "count": 473}, ...}
            if isinstance(data, dict) and service in data:
                service_data = data[service]
                count = int(service_data.get("count", 0))
                cost = service_data.get("cost", 0)
                
                return {
                    "available": count,
                    "price": float(cost) if cost else 0,
                }
                
        except Exception as e:
            logger.error(f"Failed to check DaisySMS stock: {e}")
            
        return {"available": 0, "error": "Unable to check stock"}

    def get_price(self, service, country=187):
        """
        Get price for a service using getPrices.
        """
        try:
            result = self._request({
                "action": "getPrices",
                "country": country,
            })
            
            data = json.loads(result)
            
            # Format: {"amazon": {"cost": 0.3, "count": 473}, ...}
            if isinstance(data, dict) and service in data:
                cost = data[service].get("cost", 0)
                
                if cost:
                    return {
                        "success": True,
                        "price_usd": float(cost),
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get DaisySMS price: {e}")
            
        return {
            "success": False,
            "price_usd": 0,
        }

    def purchase(self, service, country=187, max_price=None, areas=None, carriers=None):
        """
        Rent a number using getNumber.
        Returns: {"order_id": "...", "phone_number": "...", "status": "waiting"}
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

        result = self._request(params)

        if result.startswith("ACCESS_NUMBER:"):
            parts = result.split(":")
            return {
                "order_id": parts[1],
                "phone_number": parts[2],
                "status": "waiting",
            }
        else:
            raise Exception(f"DaisySMS purchase failed: {result}")

    def check_sms(self, order_id):
        """
        Check for SMS code.
        """
        result = self._request({
            "action": "getStatus",
            "id": order_id,
        })

        if result.startswith("STATUS_OK:"):
            code = result.split(":")[1]
            return {
                "status": "finished",
                "sms": code,
                "full_sms": None,
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
        """
        Cancel rental and get refund.
        """
        result = self._request({
            "action": "setStatus",
            "id": order_id,
            "status": 8,
        })

        if result == "ACCESS_CANCEL":
            return {"success": True}
        else:
            return {"success": False, "error": result}

    def mark_done(self, order_id):
        """
        Mark rental as done.
        """
        result = self._request({
            "action": "setStatus",
            "id": order_id,
            "status": 6,
        })
        return result == "ACCESS_ACTIVATION"