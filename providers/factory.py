from providers.daisysms import DaisySMSProvider
from providers.smsbower import SMSBowerProvider

# Accept both server names and provider names — orders store whichever
# they were given, and external code may pass either.
ALIASES = {
    "server1": "server1",
    "smsbower": "server1",
    "server2": "server2",
    "daisysms": "server2",
    "daisy": "server2",
}


def get_provider(server="server2"):
    """
    Servers:
    - server1 / smsbower: SMSBower (General, 150+ countries)
    - server2 / daisysms: DaisySMS (USA only)
    """
    key = ALIASES.get(str(server or "server2").strip().lower())
    if key is None:
        raise ValueError(f"Unsupported server/provider: {server}")

    if key == "server1":
        # SMSBower reads SMSBOWER_API_KEY from settings itself
        return SMSBowerProvider()

    from django.conf import settings
    api_key = getattr(settings, "DAISYSMS_API_KEY", "")
    return DaisySMSProvider(api_key=api_key)