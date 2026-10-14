from providers.daisysms import DaisySMSProvider
from providers.instantnums import InstantNumsProvider


def get_provider(server="server2"):
    """
    Servers:
    - server1: InstantNums (General, 150+ countries)
    - server2: DaisySMS (USA only)
    """
    server = server.lower()

    if server == "server1":
        # InstantNums reads INSTANTNUMS_API_KEY / INSTANTNUMS_BASE_URL
        # from settings itself — no constructor args needed.
        return InstantNumsProvider()

    if server == "server2":
        from django.conf import settings
        api_key = getattr(settings, "DAISYSMS_API_KEY", "")
        return DaisySMSProvider(api_key=api_key)

    raise ValueError(f"Unsupported server: {server}")