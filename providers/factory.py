from providers.daisysms import DaisySMSProvider


def get_provider(server="server2"):
    """
    Servers:
    - server2: DaisySMS (USA only)
    """
    providers = {
        "server2": DaisySMSProvider,
    }

    provider_class = providers.get(server.lower())

    if not provider_class:
        raise ValueError(f"Unsupported server: {server}")

    from django.conf import settings
    api_key = getattr(settings, "DAISYSMS_API_KEY", "")
    return provider_class(api_key=api_key)