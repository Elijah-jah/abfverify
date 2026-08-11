import logging
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django_ratelimit.decorators import ratelimit
from django.utils import timezone
from django.views.decorators.cache import never_cache
from countries.models import Country
from services.models import Service
from wallet.models import Wallet, Transaction
from pricing.models import Pricing
from providers.factory import get_provider
from orders.models import Order
from .models import User, UserSettings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='10/m', method='POST', block=True)
@login_required
def cancel_order_view(request):
    if request.method != "POST":
        return redirect("sms")

    order_id = request.POST.get("order_id")

    if not order_id:
        messages.error(request, "Invalid order request.")
        return redirect("sms")

    order = Order.objects.filter(id=order_id, user=request.user).first()

    if not order:
        messages.error(request, "Order not found.")
        return redirect("sms")

    if order.status == "cancelled":
        messages.info(request, "This order has already been cancelled.")
        return redirect("sms")

    # Cannot cancel if already paid (SMS received)
    if order.status == "completed":
        messages.error(request, "This order cannot be cancelled. SMS code has already been received.")
        return redirect("sms")

    if order.status not in ("waiting", "pending"):
        messages.error(request, "This order cannot be cancelled.")
        return redirect("sms")

    # Get correct provider based on server stored in order
    provider = get_provider(server=order.provider)

    # Try to cancel with provider (free up the number)
    try:
        provider.cancel_order(order.provider_order_id)
    except Exception as e:
        logger.warning("Provider cancel failed for order %s on server %s: %s", order.order_id, order.provider, str(e))

    order.status = "cancelled"
    order.save(update_fields=["status", "updated_at"])

    messages.success(request, "Your order has been cancelled. No charge was made.")
    return redirect("sms")


@login_required
def orders_view(request):

    user_orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at")

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "panel/orders.html",
        {
            "orders": user_orders,
            "user_wallet": wallet,
        }
    )


@ratelimit(key='user', rate='10/m', method='POST', block=True)
@login_required
def sms_view(request):

    countries = Country.objects.filter(status="active")
    services = Service.objects.filter(status="active")

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )


    if request.method == "POST":

        # Get server selection
        server = request.POST.get("server", "server3")

        # Validate server
        if server not in ("server1", "server2", "server3"):
            messages.error(request, "Invalid server selected.")
            return redirect("sms")

        # Server 1 - Coming Soon
        if server == "server1":
            messages.error(request, "Server 1 is coming soon.")
            return redirect("sms")

        country = get_object_or_404(
            Country,
            id=request.POST.get("country"),
            status="active",
        )

        service = get_object_or_404(
            Service,
            id=request.POST.get("service"),
            status="active",
        )

        # Server 2 (DaisySMS) — USA only validation
        if server == "server2" and country.iso_code.upper() not in ("US", "USA"):
            messages.error(request, "Server 2 only supports USA numbers.")
            return redirect("sms")

        try:
            pricing = Pricing.objects.get(
                country=country,
                service=service,
                status="active",
                is_available=True,
            )
        except Pricing.DoesNotExist:
            messages.error(request, "This service is currently unavailable.")
            return redirect("sms")

                # Check wallet balance including pending orders
        pending_total = Order.objects.filter(
            user=request.user,
            status__in=["waiting", "pending"],
        ).aggregate(total=Sum("price"))["total"] or 0

        total_needed = pending_total + pricing.selling_price

        if wallet.balance < total_needed:
            if pending_total > 0:
                messages.error(
                    request,
                    "Insufficient balance. You have pending orders. Cancel uncompleted orders and try again."
                )
            else:
                messages.error(request, "Your wallet balance is too low. Add funds to continue.")
            return redirect("wallet")

        # Prevent duplicate requests within 10 seconds
        recent_order = Order.objects.filter(
            user=request.user,
            country=country,
            service=service,
            status="waiting",
            created_at__gte=timezone.now() - timedelta(seconds=10),
        ).exists()

        if recent_order:
            messages.warning(request, "Your previous request is still being processed.")
            return redirect("sms")

        # Get provider based on server
        provider = get_provider(server=server)

        # Use correct identifiers based on server
        if server == "server2":
            service_identifier = service.code
            country_identifier = 187
        else:
            service_identifier = service.provider_id
            country_identifier = country.provider_id

        try:
            # Check provider stock
            stock = provider.check_stock(
                service=service_identifier,
                country=country_identifier,
            )

            if stock.get("available", 0) <= 0:
                messages.error(request, "This service is currently out of stock.")
                return redirect("sms")

            # Purchase number from provider
            result = provider.purchase(
                service=service_identifier,
                country=country_identifier,
            )

        except Exception as e:
            logger.exception("Provider purchase failed for user %s, country %s, service %s, server %s: %s", 
                             request.user.id, country.name, service.name, server, str(e))
            messages.error(request, "Unable to complete your request. Please try again later.")
            return redirect("sms")

        # Create order — NO wallet deduction yet
        Order.objects.create(
            user=request.user,
            country=country,
            service=service,
            phone_number=result["phone_number"],
            provider=server,
            provider_order_id=result["order_id"],
            price=pricing.selling_price,
            status="waiting",
        )

        messages.success(request, "Virtual number reserved. You will only be charged if SMS is received.")
        return redirect("sms")

    # Load all active orders (waiting + received)
    active_orders = (
        Order.objects.filter(
            user=request.user,
            status__in=["waiting", "received"],
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "panel/sms.html",
        {
            "countries": countries,
            "services": services,
            "user_wallet": wallet,
            "active_orders": active_orders,
        },
    )


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def register_view(request):

    if request.user.is_authenticated:
        logger.info("Authenticated user %s tried to access register page", request.user.id)
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if not username or not email or not password1 or not password2:
            logger.warning("Registration failed: missing fields")
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "accounts/register.html",
                {
                    "username": username,
                    "email": email,
                },
            )

        if password1 != password2:
            logger.warning("Registration failed for %s: passwords do not match", email)
            messages.error(request, "Passwords do not match.")
            return render(
                request,
                "accounts/register.html",
                {
                    "username": username,
                    "email": email,
                },
            )

        if User.objects.filter(email=email).exists():
            logger.warning("Registration failed: email already registered - %s", email)
            messages.error(request, "Email already registered.")
            return render(
                request,
                "accounts/register.html",
                {
                    "username": username,
                    "email": email,
                },
            )

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
        )

        # Activate the user immediately
        user.is_active = True
        user.save()

        logger.info("New user registered: %s (ID: %s)", username, user.id)

        # Create wallet if it doesn't already exist
        Wallet.objects.get_or_create(
            user=user,
            defaults={"balance": 0},
        )

        logger.info("Wallet created for user %s", user.id)

        # Automatically log the user in
        login(request, user)

        logger.info("User %s logged in after registration", user.id)

        messages.success(
            request,
            f"Welcome to ABFverify, {user.username}!"
        )

        # Go straight to the dashboard
        return redirect("dashboard")

    return render(
        request,
        "accounts/register.html",
    )



@login_required
def settings_view(request):

    settings, created = UserSettings.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        settings.email_notifications = (
            "email_notifications" in request.POST
        )

        settings.order_notifications = (
            "order_notifications" in request.POST
        )

        settings.save()

        messages.success(
            request,
            "Settings updated successfully."
        )

    return render(
        request,
        "panel/settings.html",
        {
            "settings": settings
        }
    )



@never_cache
def logout_view(request):

    logout(request)

    response = redirect("website:home")

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response



@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):

    if request.user.is_authenticated:
        logger.info("Authenticated user %s tried to access login page", request.user.id)
        return redirect("dashboard")

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(
            request,
            email=email,
            password=password
        )

        if user:

            if not user.is_active:
                logger.warning("Login failed for %s: account is inactive", email)
                messages.warning(
                    request,
                    "Please verify your email before logging in."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "email": email,
                    }
                )

            login(request, user)
            logger.info("User %s logged in successfully", user.id)
            return redirect("dashboard")


        logger.warning("Login failed for %s: invalid credentials", email)
        messages.error(
            request,
            "Invalid email or password."
        )

        return render(
            request,
            "accounts/login.html",
            {
                "email": email,
            }
        )

    return render(
        request,
        "accounts/login.html"
    )


# ==========================
# USER DASHBOARD
# ==========================

@login_required
def dashboard(request):
    # --- POPUP NOTICE LOGIC ---
    show_notice = not request.session.get('dashboard_notice_dismissed', False)

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    transactions = Transaction.objects.filter(
        user=request.user
    )

    total_transactions = transactions.count()

    # Calculate total spent from payment transactions (new way) and orders (old way)
    total_spent_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type="payment",
        status="successful",
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_spent_orders = Order.objects.filter(
        user=request.user,
        status__in=["completed", "received"],
    ).aggregate(total=Sum("price"))["total"] or 0

    # Use the higher value to catch all deductions
    total_spent = max(total_spent_transactions, total_spent_orders)

    context = {
        "wallet": wallet,
        "total_transactions": total_transactions,
        "total_spent": total_spent,

        # Temporary values until Orders/SMS backend
        "active_orders": 0,
        "total_sms": 0,

        # --- POPUP FLAG ---
        "show_notice": show_notice,
    }

    return render(
        request,
        "panel/dashboard.html",
        context
    )


@login_required
def dismiss_notice(request):
    """Called when user clicks 'Got it, Thanks' on the popup"""
    if request.method == 'POST':
        request.session['dashboard_notice_dismissed'] = True
    return redirect('dashboard')

# ==========================
# WALLET PAGE
# ==========================

@login_required
def wallet_view(request):

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )


    return render(
        request,
        "panel/wallet.html",
        {
            "wallet": wallet
        }
    )



# ==========================
# TRANSACTIONS
# ==========================
@login_required
def transactions_page(request):

    transactions = Transaction.objects.filter(
        user=request.user
    ).order_by("-created_at")

    user_wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    # Calculate total spent from payment transactions (new way) and orders (old way)
    total_spent_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type="payment",
        status="successful",
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_spent_orders = Order.objects.filter(
        user=request.user,
        status__in=["completed", "received"],
    ).aggregate(total=Sum("price"))["total"] or 0

    # Use the higher value to catch all deductions
    total_spent = max(total_spent_transactions, total_spent_orders)

    return render(
        request,
        "panel/transactions.html",
        {
            "transactions": transactions,
            "user_wallet": user_wallet,
            "total_spent": total_spent,
        }
    )

# ==========================
# SERVICES
# ==========================

@login_required
def services_view(request):

    return render(
        request,
        "panel/services.html"
    )



def landing_view(request):
    return render(request, "website/home.html")



# ============================================================
# PASSWORD RESET VIEWS
# ============================================================

import requests

def forgot_password_view(request):
    """Show forgot password form and send reset email via Brevo HTTP API."""
    if request.user.is_authenticated:
        logger.info("Authenticated user %s tried to access forgot password", request.user.id)
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            return render(request, "accounts/forgot_password.html", {
                "error": "Please enter your email address."
            })

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, "accounts/reset_email_sent.html")

        # Generate token and UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Build reset URL
        domain = request.get_host()
        if request.META.get('HTTP_X_FORWARDED_PROTO') == 'https':
            protocol = 'https'
        else:
            protocol = 'https' if request.is_secure() else 'http'

        reset_url = f"{protocol}://{domain}/accounts/password-reset-confirm/{uid}/{token}/"

        # Render email body
        html_content = render_to_string("accounts/password_reset_email.html", {
            "user": user,
            "reset_url": reset_url,
            "protocol": protocol,
            "domain": domain,
        })

        # Send via Brevo HTTP API
        brevo_api_key = getattr(settings, 'BREVO_API_KEY', None)
        
        logger.info("Brevo API Key present: %s", bool(brevo_api_key))
        
        if not brevo_api_key:
            logger.error("BREVO_API_KEY is not set in settings")
            return render(request, "accounts/forgot_password.html", {
                "error": "Email service not configured. Please contact support."
            })

        payload = {
            "sender": {
                "name": "ABFverify",
                "email": settings.DEFAULT_FROM_EMAIL or "noreply@abfverify.com"
            },
            "to": [{"email": email, "name": user.username or email}],
            "subject": "Password reset for your ABFverify account",
            "htmlContent": html_content
        }

        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "accept": "application/json",
                    "api-key": brevo_api_key,
                    "content-type": "application/json"
                },
                json=payload,
                timeout=10
            )
            
            logger.info("Brevo API status: %s, response: %s", response.status_code, response.text[:500])
            
            if response.status_code in (200, 201, 202):
                logger.info("Password reset email sent to %s via Brevo API", email)
                return render(request, "accounts/reset_email_sent.html")
            else:
                logger.error("Brevo API error %s: %s", response.status_code, response.text)
                return render(request, "accounts/forgot_password.html", {
                    "error": f"Email service error {response.status_code}. Please contact support."
                })
                
        except Exception as e:
            logger.error("Brevo API request failed for %s: %s", email, str(e))
            return render(request, "accounts/forgot_password.html", {
                "error": "Failed to send email. Please try again later."
            })

    return render(request, "accounts/forgot_password.html")


def reset_email_sent_view(request):
    """Show 'check your email' confirmation page."""
    return render(request, "accounts/reset_email_sent.html")


def reset_password_confirm_view(request, uidb64, token):
    """Validate token and let user set a new password."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/reset_password.html", {
            "validlink": False,
            "error": "This password reset link is invalid or has expired."
        })

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            return redirect("password_reset_complete")
        else:
            return render(request, "accounts/reset_password.html", {
                "validlink": True,
                "form": form,
            })

    form = SetPasswordForm(user)
    return render(request, "accounts/reset_password.html", {
        "validlink": True,
        "form": form,
    })


def reset_password_complete_view(request):
    """Password successfully changed."""
    return render(request, "accounts/password_reset_complete.html")

@ratelimit(key='user', rate='5/m', method='POST', block=True)
@login_required
def change_password_view(request):

    if request.method == "POST":

        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Check current password
        if not request.user.check_password(current_password):
            messages.error(
                request,
                "Your current password is incorrect."
            )
            return redirect("change_password")

        # Check passwords match
        if new_password != confirm_password:
            messages.error(
                request,
                "New passwords do not match."
            )
            return redirect("change_password")

        # Prevent using same password
        if request.user.check_password(new_password):
            messages.error(
                request,
                "Your new password cannot be the same as your current password."
            )
            return redirect("change_password")

        # Validate password
        try:
            validate_password(new_password, request.user)

        except ValidationError as e:

            for error in e.messages:
                messages.error(request, error)

            return redirect("change_password")

        # Save new password
        request.user.set_password(new_password)
        request.user.save()

        # Keep the user logged in
        update_session_auth_hash(request, request.user)

        messages.success(
            request,
            "Password changed successfully."
        )

        return redirect("change_password")

    return render(
        request,
        "panel/change_password.html"
    )


def privacy_policy(request):
    return render(request, "website/privacypolicy.html")


def terms_of_service(request):
    return render(request, "website/termsofservice.html")

def ratelimited_error(request, exception=None):
    return render(request, '429.html', status=429)