from .models import Wallet


def wallet_balance(request):
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(
            user=request.user
        )

        return {
            "user_wallet": wallet
        }

    return {
        "user_wallet": None
    }