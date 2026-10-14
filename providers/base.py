class BaseProvider:
    """
    Interface that every SMS provider must implement.
    server1 -> InstantNumsProvider (General)
    server2 -> DaisySMSProvider    (USA only)
    """

    def get_balance(self):
        raise NotImplementedError

    def get_countries(self):
        raise NotImplementedError

    def get_services(self, country=None):
        raise NotImplementedError

    def get_price(self, service, country):
        raise NotImplementedError

    def check_stock(self, service, country):
        """Optional: check availability before purchase."""
        raise NotImplementedError

    def purchase(self, service, country):
        raise NotImplementedError

    def check_sms(self, order_id):
        raise NotImplementedError

    def cancel(self, order_id):
        raise NotImplementedError