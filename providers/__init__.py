def __init__(self, api_key: str, proxy: str | None = None):
    self.api_key = api_key
    self._session = requests.Session()
    self._session.headers.update(BROWSER_HEADERS)
    if proxy:
        self._session.proxies = {"http": proxy, "https": proxy}