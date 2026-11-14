from providers.daisysms import DaisySMSProvider

# Accept both server names and provider names — orders store whichever
# they were given, and external code may pass either.
ALIASES = {
    "server2": "server2",
    "daisysms": "server2",
    "daisy": "server2",
}


def get_provider(server="server2"):
    """
    Servers:
    - server2 / daisysms: DaisySMS (USA)
    - server1: retired (InstantNums removed) — SMSBower lands here next
    """
    key = ALIASES.get(str(server or "server2").strip().lower())
    if key is None:
        raise ValueError(f"Unsupported server/provider: {server}")

    from django.conf import settings
    api_key = getattr(settings, "DAISYSMS_API_KEY", "")
    return DaisySMSProvider(api_key=api_key)