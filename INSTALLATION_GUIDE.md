# ABFverify — Referral Program + Code Redemption Update

## What this update adds

1. **Referral codes for everyone** — every existing user AND every new user gets a unique referral code (existing users get theirs automatically when you run the migration).
2. **Tiered referral rewards** — when people a user invited make their **first deposit**, the referrer earns: **2 → ₦500, 5 → ₦800, 10 → ₦1,000, 20 → ₦2,000, 30 → ₦4,000**. Each tier pays once, automatically.
3. **₦200 instant signup bonus** — a new user who registers with a referral code gets ₦200 credited immediately.
4. **Signup page** — optional "Have a referral code?" field (also auto-filled when someone opens a referral link).
5. **Dashboard referral card** — pops up on login, shows the user's code + copy button + "No thanks" + "Go to Settings to view more". Re-appears every **6 hours** (tracked on the server, works on any device).
6. **Settings page** — referral link + code with copy buttons, invited/deposited/earned stats, animated **battery-style progress bar** toward the next reward, all reward tiers, and a "Join Telegram channel for ABFverify codes" card.
7. **Floating redeem icon** — a gift icon floats above the Telegram button on every panel page. Clicking it opens a "Redeem ABFverify Code" card. Codes are **one-time use** and credit the wallet instantly.
8. **Admin code generation** — in Django admin (`/semilore/`) under **Referrals → Redeem codes**: type any code (or leave blank to auto-generate), set the amount, Save.
9. **Transactions** — referral bonuses and code redemptions appear in the user's transaction history.

Everything uses your existing theme variables, so **dark/light mode and mobile responsiveness** work automatically.

---

## STEP 1 — Copy the new files into your project

Copy these folders/files from this package into your project root (`C:\Users\user\OneDrive\Desktop\ABFverify\`). They slot into place — nothing gets overwritten:

```
referrals\                                    (NEW app - whole folder)
wallet\migrations\0011_alter_transaction_transaction_type.py   (NEW file only)
static\css\referrals.css                      (NEW file)
static\js\referrals.js                        (NEW file)
```

> Your project already has `wallet\migrations\` — you're only dropping the single new `0011_...` file into it, not replacing the folder.

---

## STEP 2 — `config\settings.py`

In `INSTALLED_APPS`, find `"finance",` and add `"referrals",` after it:

```python
    "marketplace",
    "boost",
    'django.contrib.humanize',
    "finance",
    "referrals",          # <-- ADD THIS LINE
]
```

---

## STEP 3 — `config\urls.py`

Find this line:

```python
    path("accounts/", include("boost.urls")),
```

Add this right after it:

```python
    path("accounts/", include("referrals.urls")),
```

---

## STEP 4 — `wallet\models.py` (add transaction types)

Find the `TRANSACTION_TYPES` tuple inside the `Transaction` model:

```python
    TRANSACTION_TYPES = (
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("payment", "Payment"),
        ("refund", "Refund"),
    )
```

Replace it with:

```python
    TRANSACTION_TYPES = (
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("referral", "Referral Bonus"),
        ("redeem", "Code Redemption"),
    )
```

---

## STEP 5 — `accounts\views.py`

### 5a. Add one import

Find this line near the top:

```python
from marketplace.models import LogPurchase
```

Add this line right after it:

```python
from referrals.models import ReferralProfile, ReferralReward, REFERRAL_TIERS
```

### 5b. Replace the WHOLE `register_view` function

Delete your entire current `register_view` function (from `def register_view(request):` down to its final `return render(request, "accounts/register.html",)` ) and paste this instead:

```python
def register_view(request):

    if request.user.is_authenticated:
        logger.info("Authenticated user %s tried to access register page", request.user.id)
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        referral_code = (request.POST.get("referral_code") or "").strip()

        if not username or not email or not password1 or not password2:
            logger.warning("Registration failed: missing fields")
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "accounts/register.html",
                {
                    "username": username,
                    "email": email,
                    "referral_code": referral_code,
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
                    "referral_code": referral_code,
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
                    "referral_code": referral_code,
                },
            )

        # Referral code is OPTIONAL - but if one was typed, it must be valid
        if referral_code and not ReferralProfile.objects.filter(
            code__iexact=referral_code
        ).exists():
            messages.error(
                request,
                "That referral code is invalid. Check it or leave it blank."
            )
            return render(
                request,
                "accounts/register.html",
                {
                    "username": username,
                    "email": email,
                    "referral_code": referral_code,
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

        # Referral: link to the referrer and pay the N200 instant signup bonus
        if referral_code:
            try:
                from referrals.services import attach_referrer
                referrer = attach_referrer(user, referral_code)
                if referrer:
                    messages.success(
                        request,
                        "Referral applied - N200 bonus credited to your wallet!"
                    )
            except Exception:
                logger.exception("Referral attach failed for user %s", user.id)

        # Automatically log the user in
        login(request, user)

        logger.info("User %s logged in after registration", user.id)

        messages.success(
            request,
            f"Welcome to ABFverify, {user.username}!"
        )

        # Go straight to the dashboard
        return redirect("dashboard")

    # GET - prefill the referral code when arriving from a referral link (?ref=CODE)
    return render(
        request,
        "accounts/register.html",
        {
            "referral_code": (request.GET.get("ref") or "").strip(),
        },
    )
```

### 5c. Update the `dashboard` view (referral card data)

Inside `def dashboard(request):`, find the `context = {` line near the end. Right **before** it, paste this block:

```python
    # --- REFERRAL CARD (shows on login, re-shows every 6 hours) ---
    referral_profile, _ = ReferralProfile.objects.get_or_create(user=request.user)
    show_referral_card = (
        referral_profile.card_dismissed_at is None
        or timezone.now() - referral_profile.card_dismissed_at >= timedelta(hours=6)
    )
    protocol = "https" if (
        request.is_secure()
        or request.META.get("HTTP_X_FORWARDED_PROTO") == "https"
    ) else "http"
    referral_link = (
        f"{protocol}://{request.get_host()}"
        f"/accounts/register/?ref={referral_profile.code}"
    )
```

Then inside the `context = { ... }` dict, add these three entries (anywhere inside the dict):

```python
        "show_referral_card": show_referral_card,
        "referral_code": referral_profile.code,
        "referral_link": referral_link,
```

### 5d. Replace the WHOLE `settings_view` function

Delete your entire current `settings_view` function and paste this instead:

```python
def settings_view(request):

    user_settings, created = UserSettings.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        user_settings.email_notifications = (
            "email_notifications" in request.POST
        )

        user_settings.order_notifications = (
            "order_notifications" in request.POST
        )

        user_settings.save()

        messages.success(
            request,
            "Settings updated successfully."
        )

    # ==========================
    # REFERRAL PROGRAM DATA
    # ==========================
    referral_profile, _ = ReferralProfile.objects.get_or_create(user=request.user)

    protocol = "https" if (
        request.is_secure()
        or request.META.get("HTTP_X_FORWARDED_PROTO") == "https"
    ) else "http"
    referral_link = (
        f"{protocol}://{request.get_host()}"
        f"/accounts/register/?ref={referral_profile.code}"
    )

    invited_total = ReferralProfile.objects.filter(
        referred_by=request.user
    ).count()

    qualified_count = ReferralProfile.objects.filter(
        referred_by=request.user, qualified=True
    ).count()

    earned_tiers = set(
        ReferralReward.objects.filter(referrer=request.user)
        .values_list("tier", flat=True)
    )

    total_earned = sum(
        ReferralReward.objects.filter(referrer=request.user)
        .values_list("amount", flat=True)
    )

    tiers = []
    for tier_count, tier_amount in REFERRAL_TIERS:
        tiers.append({
            "count": tier_count,
            "amount": f"{tier_amount:.0f}",
            "earned": tier_count in earned_tiers,
        })

    # Progress toward the NEXT unpaid tier (battery bar)
    next_tier = None
    next_tier_amount = None
    for tier_count, tier_amount in REFERRAL_TIERS:
        if tier_count not in earned_tiers and qualified_count < tier_count:
            next_tier = tier_count
            next_tier_amount = f"{tier_amount:.0f}"
            break

    if next_tier:
        progress_percent = min(100, int(round(qualified_count / next_tier * 100)))
    else:
        progress_percent = 100

    return render(
        request,
        "panel/settings.html",
        {
            "settings": user_settings,
            "referral_code": referral_profile.code,
            "referral_link": referral_link,
            "invited_total": invited_total,
            "qualified_count": qualified_count,
            "total_earned": total_earned,
            "tiers": tiers,
            "next_tier": next_tier,
            "next_tier_amount": next_tier_amount,
            "progress_percent": progress_percent,
        }
    )
```

---

## STEP 6 — `wallet\views.py` (trigger rewards on first deposit)

Inside `pocketfi_webhook`, find this line near the end:

```python
    print(f"POCKETFI WEBHOOK: credited {wallet.user.email} ₦{amount}")
```

Paste this block right **before** that line:

```python
    # Referral: a FIRST successful deposit qualifies this user and
    # pays any due tier rewards to whoever referred them.
    try:
        from referrals.services import process_first_deposit
        process_first_deposit(wallet.user)
    except Exception:
        import traceback
        traceback.print_exc()

```

---

## STEP 7 — `templates\accounts\register.html` (referral code field)

Find this line:

```html
            <!-- TERMS CHECKBOX -->
```

Paste this block right **before** it:

```html
            <!-- REFERRAL CODE (optional) -->
            <div class="input-group">

                <label>Referral Code <span style="opacity:.6;font-weight:400;">(optional)</span></label>

                <input
                    type="text"
                    name="referral_code"
                    value="{{ referral_code|default:'' }}"
                    placeholder="Have a referral code? Enter it here"
                    autocomplete="off">

            </div>

```

---

## STEP 8 — `templates\panel\settings.html` (referral + Telegram sections)

Find this line:

```html
    <!-- Notifications (single, clean form — was nested/invalid before) -->
```

Paste this entire block right **before** it:

```html
    <!-- Referral Program -->
    <div class="st-card st-card-full">

        <div class="st-card-header">
            <div class="st-card-icon">
                <i class="fas fa-users"></i>
            </div>
            <h3>Referral Program</h3>
        </div>

        <p class="ref-lead">
            Invite friends to ABFverify and earn cash rewards straight to your
            wallet when they make their first deposit.
        </p>

        <div class="st-field">
            <label>Your Referral Link</label>
            <div class="ref-link-row">
                <input type="text" value="{{ referral_link }}" readonly>
                <button type="button" class="ref-copy-btn" data-copy="{{ referral_link }}">
                    <i class="fas fa-copy"></i> Copy Link
                </button>
            </div>
        </div>

        <div class="st-field">
            <label>Your Referral Code</label>
            <div class="ref-link-row">
                <input type="text" value="{{ referral_code }}" readonly>
                <button type="button" class="ref-copy-btn" data-copy="{{ referral_code }}">
                    <i class="fas fa-copy"></i> Copy Code
                </button>
            </div>
        </div>

        <!-- Stats -->
        <div class="ref-stats">
            <div class="ref-stat">
                <span class="ref-stat-num">{{ invited_total }}</span>
                <span class="ref-stat-label">Invited</span>
            </div>
            <div class="ref-stat">
                <span class="ref-stat-num">{{ qualified_count }}</span>
                <span class="ref-stat-label">Deposited</span>
            </div>
            <div class="ref-stat">
                <span class="ref-stat-num">₦{{ total_earned|floatformat:0|intcomma }}</span>
                <span class="ref-stat-label">Earned</span>
            </div>
        </div>

        <!-- Battery progress toward next reward -->
        {% if next_tier %}
        <div class="ref-progress-block">
            <div class="ref-progress-head">
                <span>
                    Next reward: <strong>₦{{ next_tier_amount }}</strong>
                    at {{ next_tier }} depositing referrals
                </span>
                <span class="ref-progress-pct">{{ progress_percent }}%</span>
            </div>
            <div class="ref-battery">
                <div class="ref-battery-fill" data-progress="{{ progress_percent }}"></div>
            </div>
        </div>
        {% else %}
        <p class="ref-maxed">
            <i class="fas fa-crown"></i>
            You've unlocked every referral reward. Keep inviting!
        </p>
        {% endif %}

        <!-- Reward tiers -->
        <div class="ref-tiers">
            {% for tier in tiers %}
            <div class="ref-tier {% if tier.earned %}earned{% endif %}">
                <span class="ref-tier-count">
                    <i class="fas fa-user-group"></i> {{ tier.count }} users
                </span>
                <span class="ref-tier-amount">₦{{ tier.amount }}</span>
                {% if tier.earned %}
                <span class="ref-tier-badge"><i class="fas fa-check"></i> Paid</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>

    </div>

    <!-- Telegram / ABFverify Codes -->
    <div class="st-card st-card-full ref-telegram">

        <div class="st-card-header">
            <div class="st-card-icon">
                <i class="fab fa-telegram"></i>
            </div>
            <h3>ABFverify Codes</h3>
        </div>

        <div class="st-row">
            <div class="st-row-text">
                <h4>Join our Telegram channel</h4>
                <p>
                    Join the ABFverify Telegram channel to enjoy ABFverify code
                    redeeming — redeem codes we drop there and get any amount
                    credited straight to your wallet.
                </p>
            </div>
            <a href="https://t.me/abflogs" target="_blank" class="st-btn">
                <i class="fab fa-telegram"></i> Join Channel
            </a>
        </div>

    </div>

```

---

## STEP 9 — `templates\panel\dashboard.html` (6-hour referral card)

Go to the **very bottom** of the file. Paste this block right **before** the final `{% endblock %}`:

```html
{% if show_referral_card %}
<!-- REFERRAL CARD - shows on login, re-shows every 6 hours -->
<div class="ref-modal" id="referralCardModal" data-dismiss-url="{% url 'dismiss_referral_card' %}">
    {% csrf_token %}

    <div class="ref-modal-box">

        <button type="button" class="ref-modal-close" data-ref-dismiss aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
        </button>

        <div class="ref-modal-hero">
            <div class="ref-modal-icon">
                <i class="fa-solid fa-users"></i>
            </div>
            <h3>Refer friends &amp; earn cash!</h3>
            <p class="ref-modal-sub">
                Refer <strong>2 people</strong> and get <strong>₦500</strong> credited
                to your wallet when they make their first deposit. Keep going —
                earn up to <strong>₦4,000</strong>!
            </p>
        </div>

        <span class="ref-code-label">Your referral code</span>
        <div class="ref-code-box">
            <code>{{ referral_code }}</code>
            <button type="button" class="ref-copy-btn" data-copy="{{ referral_link }}">
                <i class="fa-regular fa-copy"></i> Copy Link
            </button>
        </div>

        <div class="ref-modal-actions">
            <a href="{% url 'settings' %}" class="ref-btn ref-btn-primary">
                Go to Settings to view more
            </a>
            <button type="button" class="ref-btn ref-btn-ghost" data-ref-dismiss>
                No thanks
            </button>
        </div>

    </div>

</div>
{% endif %}

```

---

## STEP 10 — `templates\panel\dashboard_base.html` (floating redeem icon + modal)

This file needs **three** small edits.

### 10a. Load the CSS

Find:

```html
<link rel="stylesheet" href="{% static 'css/toast.css' %}">
```

Add this line right after it:

```html
<link rel="stylesheet" href="{% static 'css/referrals.css' %}">
```

### 10b. Add the floating gift icon

Find the Telegram float:

```html
<a href="https://t.me/abflogs" target="_blank" class="support-float" aria-label="Contact Support">
    <i class="fa-brands fa-telegram"></i>
    <span class="support-tooltip">Support</span>
</a>
```

Add this right **before** it:

```html
<button type="button" class="redeem-float" id="redeemFloatBtn" aria-label="Redeem ABFverify code">
    <i class="fa-solid fa-gift"></i>
    <span class="redeem-tooltip">Redeem Code</span>
</button>
```

### 10c. Add the redeem modal + JS

Find:

```html
{% block extra_js %}
{% endblock %}
```

Add this entire block right **before** it:

```html
<!-- REDEEM CODE MODAL -->
<div class="redeem-modal" id="redeemModal">

    <div class="redeem-box">

        <button type="button" class="redeem-close" data-redeem-close aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
        </button>

        <div class="redeem-icon">
            <i class="fa-solid fa-gift"></i>
        </div>

        <h3>Redeem ABFverify Code</h3>

        <p class="redeem-sub">
            Enter your code below and the amount on it will be
            credited straight to your wallet.
        </p>

        <form id="redeemForm" action="{% url 'redeem_code' %}" method="POST">
            {% csrf_token %}

            <div class="redeem-input-wrap">
                <i class="fa-solid fa-ticket"></i>
                <input
                    type="text"
                    id="redeemCodeInput"
                    class="redeem-input"
                    placeholder="Enter your code"
                    autocomplete="off"
                    maxlength="32">
            </div>

            <button type="submit" class="redeem-submit" id="redeemSubmitBtn">
                <i class="fa-solid fa-gift"></i> Redeem Code
            </button>

        </form>

        <p class="redeem-note">
            <i class="fa-solid fa-circle-info"></i>
            Codes are one-time use only. Get codes on our
            <a href="https://t.me/abflogs" target="_blank">Telegram channel</a>.
        </p>

    </div>

</div>

<script src="{% static 'js/referrals.js' %}"></script>

```

---

## STEP 11 — Run it

In your project folder (virtualenv activated):

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

The `migrate` command creates the new tables **and automatically generates a referral code for every existing user** — nobody is left out.

Then deploy the same way you normally deploy (the same two commands on your server, then restart the app).

---

## STEP 12 — How to use it

**Generate a redeem code (admin):**
1. Go to `/semilore/` → **Referrals → Redeem codes → Add**
2. Type any code you want (or leave it blank — one is auto-generated)
3. Enter the amount (e.g. `500`)
4. Save. The first user to redeem it gets that amount; then it's dead forever.

**Check referral activity (admin):**
- **Referral profiles** — every user's code, who referred them, whether they've deposited
- **Referral rewards** — every tier payout that has been made

**Quick test checklist:**
- [ ] Register a new account **with** a referral code → wallet starts at ₦200, a "Referral Bonus" transaction appears
- [ ] Register without a code → works normally, ₦0
- [ ] Invalid code → clear error message, code field keeps what you typed
- [ ] Dashboard card appears → "No thanks" hides it → it comes back after 6 hours (to test instantly, in Django admin open that user's **Referral profile** and clear the **Card dismissed at** field)
- [ ] Settings page shows link, code, stats, battery bar, tiers, Telegram card
- [ ] Floating gift icon opens the redeem card; redeeming an admin-created code credits the wallet instantly and updates the balance in the topbar
- [ ] Same code twice → "already been used" error
- [ ] When a referred user makes their first PocketFi deposit, the referrer's wallet gets the tier reward and a "Referral Bonus" transaction appears
- [ ] Toggle dark/light theme and check both look right; check on your phone too
