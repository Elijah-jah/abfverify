class BaseProvider:

    def get_balance(self):
        raise NotImplementedError

    def get_countries(self):
        raise NotImplementedError

    def get_services(self):
        raise NotImplementedError

    def get_price(self, service, country):
        raise NotImplementedError

    def check_stock(self, service, country):
        raise NotImplementedError

    def purchase(self, service, country):
        raise NotImplementedError

    def check_sms(self, order_id):
        raise NotImplementedError

    def cancel(self, order_id):
        raise NotImplementedError