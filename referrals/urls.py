from django.urls import path

from . import views

urlpatterns = [
    path("redeem-code/", views.redeem_code_view, name="redeem_code"),
    path("referral-card/dismiss/", views.dismiss_referral_card, name="dismiss_referral_card"),
]
