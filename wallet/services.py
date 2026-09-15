import requests
from django.conf import settings
from .models import Wallet


def ensure_virtual_account(user):
    """
    Create a PocketFi virtual account for this user if they don't have one.

    Returns the wallet. If the user hasn't provided their name and phone
    yet, returns the wallet WITHOUT an account so the view can prompt them.
    """
    wallet = Wallet.objects.get_or_create(user=user)[0]

    if wallet.virtual_account_number:
        return wallet  # already has one

    # Never create an account with fake identity data
    if not (user.first_name and user.last_name and user.phone):
        return wallet

    url = f"{settings.POCKETFI_BASE_URL}/api/v1/virtual-accounts/create"

    headers = {
        "Authorization": f"Bearer {settings.POCKETFI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "email": user.email,
        "businessId": settings.POCKETFI_BUSINESS_ID,
        "bank": "kuda",
    }

    response = requests.post(url, json=data, headers=headers, timeout=30)
    result = response.json()

    if result.get("status") is True and result.get("banks"):
        bank = result["banks"][0]
        wallet.virtual_account_number = bank["accountNumber"]
        wallet.virtual_bank_name = bank["bankName"]
        wallet.virtual_account_name = bank["accountName"]
        wallet.save()

    return wallet