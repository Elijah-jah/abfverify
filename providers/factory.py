from providers.instantnums import InstantNumsProvider
from providers.daisysms import DaisySMSProvider


def get_provider(server="server3"):
    """
    Return the provider based on server selection.

    Servers:
    - server1: General (placeholder)
    - server2: DaisySMS (USA only)
    - server3: InstantNums (general)
    """

    providers = {
        "server1": None,
        "server2": DaisySMSProvider,
        "server3": InstantNumsProvider,
    }

    provider_class = providers.get(server.lower())

    if not provider_class:
        raise ValueError(f"Unsupported server: {server}")

    # DaisySMS needs API key from settings
    if server == "server2":
        from django.conf import settings
        api_key = getattr(settings, "DAISYSMS_API_KEY", "")
        return provider_class(api_key=api_key)

    return provider_class()