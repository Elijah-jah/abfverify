from providers.daisysms import DaisySMSProvider
from providers.instantnums import InstantNumsProvider

# Accept both server names and provider names — orders store whichever
# they were given, and external code may pass either.
ALIASES = {
    "server1": "server1",
    "server2": "server2",
    "instantnums": "server1",
    "instant nums": "server1",
    "daisysms": "server2",
    "daisy": "server2",
}


def get_provider(server="server2"):
    """
    Servers:
    - server1 / instantnums: InstantNums (General, 150+ countries)
    - server2 / daisysms:    DaisySMS (USA only)
    """
    key = ALIASES.get(str(server or "server2").strip().lower())
    if key is None:
        raise ValueError(f"Unsupported server/provider: {server}")

    if key == "server1":
        # InstantNums reads INSTANTNUMS_API_KEY / INSTANTNUMS_BASE_URL
        # from settings itself — no constructor args needed.
        return InstantNumsProvider()

    from django.conf import settings
    api_key = getattr(settings, "DAISYSMS_API_KEY", "")
    return DaisySMSProvider(api_key=api_key)