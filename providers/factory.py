from providers.instantnums import InstantNumsProvider
from providers.daisysms import DaisySMSProvider
from providers.pvapins import PVAPinsProvider


def get_provider(server="server3"):
    """
    Servers:
    - server1: General (placeholder)
    - server2: DaisySMS (USA only)
    - server3: PVAPins (general — replaced InstantNums)
    """

    providers = {
        "server1": None,
        "server2": DaisySMSProvider,
        "server3": PVAPinsProvider,
    }

    provider_class = providers.get(server.lower())

    if not provider_class:
        raise ValueError(f"Unsupported server: {server}")

    if server == "server2":
        from django.conf import settings
        api_key = getattr(settings, "DAISYSMS_API_KEY", "")
        return provider_class(api_key=api_key)

    return provider_class()