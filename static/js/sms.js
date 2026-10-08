const countrySelect = document.getElementById("countrySelect");
const serviceSelect = document.getElementById("serviceSelect");
const serverSelect = document.getElementById("serverSelect");
const priceDisplay = document.getElementById("priceDisplay");
const requestBtn = document.getElementById("requestBtn");


// ======================
// SERVER HANDLING - DYNAMIC LOAD
// ======================

async function loadCountries() {
    const server = serverSelect.value;
    if (!server) {
        countrySelect.innerHTML = '<option value="">Select Country</option>';
        serviceSelect.innerHTML = '<option value="">Select Service</option>';
        return;
    }

    try {
        const response = await fetch(`/api/countries/?server=${server}`);
        const data = await response.json();

        if (data.success) {
            countrySelect.innerHTML = '<option value="">Select Country</option>';
            data.countries.forEach(country => {
                const option = document.createElement("option");
                option.value = country.id;
                option.textContent = country.name;
                countrySelect.appendChild(option);
            });

            if (window.countryChoices) {
                window.countryChoices.destroy();
            }
            window.countryChoices = new Choices("#countrySelect", {
                searchEnabled: true,
                searchPlaceholderValue: "Search Country...",
                itemSelectText: "",
                shouldSort: false,
                allowHTML: false
            });
        }
    } catch (error) {
        console.error("Failed to load countries:", error);
    }
}

async function loadServices() {
    const server = serverSelect.value;
    if (!server) {
        serviceSelect.innerHTML = '<option value="">Select Service</option>';
        return;
    }

    try {
        const response = await fetch(`/api/services/?server=${server}`);
        const data = await response.json();

        if (data.success) {
            serviceSelect.innerHTML = '<option value="">Select Service</option>';
            data.services.forEach(service => {
                const option = document.createElement("option");
                option.value = service.id;
                option.textContent = service.name;
                serviceSelect.appendChild(option);
            });

            if (window.serviceChoices) {
                window.serviceChoices.destroy();
            }
            window.serviceChoices = new Choices("#serviceSelect", {
                searchEnabled: true,
                searchPlaceholderValue: "Search Service...",
                itemSelectText: "",
                shouldSort: false,
                allowHTML: false
            });
        }
    } catch (error) {
        console.error("Failed to load services:", error);
    }
}

// Load both countries and services when server changes
if (serverSelect) {
    serverSelect.addEventListener("change", async () => {
        priceDisplay.innerText = "₦0.00";

        await loadCountries();
        await loadServices();
    });
}


// ======================
// UPDATE PRICE (CACHED - INSTANT)
// ======================

async function updatePrice() {
    const country = countrySelect.value;
    const service = serviceSelect.value;
    const server = serverSelect ? serverSelect.value : "server3";

    if (!country || !service) {
        priceDisplay.innerText = "₦0.00";
        return;
    }

    priceDisplay.innerText = "Loading...";

    try {
        const response = await fetch(
            `/api/get-price/?country=${country}&service=${service}&server=${server}`
        );

        const data = await response.json();

        if (data.success) {
            priceDisplay.innerText = "₦" + Number(data.selling_price).toLocaleString();
        } else {
            priceDisplay.innerText = "Unavailable";
        }

    } catch (error) {
        console.error(error);
        priceDisplay.innerText = "Unavailable";
    }
}


// Only update price when BOTH country and service are selected
if (countrySelect && serviceSelect) {
    countrySelect.addEventListener("change", () => {
        if (serviceSelect.value) {
            updatePrice();
        }
    });

    serviceSelect.addEventListener("change", () => {
        if (countrySelect.value) {
            updatePrice();
        }
    });
}


// ======================
// COUNTDOWN TIMERS
// ======================

function initCountdown(timer) {

    const createdAt = timer.dataset.created;
    const session = timer.closest(".sms-session");

    if (!createdAt || !session) {
        if (session) session.style.display = "none";
        return;
    }

    const startTime = new Date(createdAt).getTime();
    const duration = 20 * 60 * 1000;

    const remaining = duration - (Date.now() - startTime);
    if (remaining <= 0) {
        timer.innerText = "00:00";
        session.style.display = "none";
        return;
    }

    function updateTimer() {

        const remaining = duration - (Date.now() - startTime);

        if (remaining <= 0) {

            timer.innerText = "00:00";

            clearInterval(timerInterval);

            session.style.display = "none";

            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);

        timer.innerText =
            String(minutes).padStart(2, "0") +
            ":" +
            String(seconds).padStart(2, "0");

    }

    updateTimer();

    const timerInterval = setInterval(updateTimer, 1000);

}

document.querySelectorAll(".sms-timer").forEach(initCountdown);


// ======================
// COPY BUTTONS
// ======================

function initCopyButtons(scope) {

    scope.querySelectorAll(".copy-btn")
    .forEach(button => {

        // Skip buttons already wired up (e.g. injected order cards)
        if (button.dataset.copyBound) return;
        button.dataset.copyBound = "1";

        button.addEventListener("click", () => {

            const text = button.dataset.copy;

            if (!text) return;

            navigator.clipboard.writeText(text)
            .then(() => {

                const icon =
                    button.querySelector("i");

                icon.classList.remove("fa-copy");
                icon.classList.add("fa-check");

                setTimeout(() => {

                    icon.classList.remove("fa-check");
                    icon.classList.add("fa-copy");

                }, 1500);

            });

        });

    });

}

initCopyButtons(document);


// ======================
// AUTO CHECK SMS
// ======================

function initSmsPolling(session) {

    const statusBox = session.querySelector(".sms-status");
    if (!statusBox) return;

    const orderId = session.dataset.orderId;
    const otpBox = session.querySelector(".otp-box");
    const copyBtn = session.querySelector(".otp-copy-btn");

    async function checkSMS() {
        try {
            const response = await fetch(
                `/api/check-sms/?order_id=${orderId}`
            );

            const data = await response.json();

            if (data.success && data.status === "finished") {
                otpBox.innerText = data.sms;
                copyBtn.disabled = false;
                copyBtn.dataset.copy = data.sms;
                statusBox.innerText = "SMS Received";
                clearInterval(smsInterval);
                return;
            }

            if (data.status === "done" || data.status === "expired" || data.status === "cancelled") {
                session.style.display = "none";
                clearInterval(smsInterval);
                return;
            }

            if (data.status === "waiting") {
                statusBox.innerText = "Waiting for SMS...";
            }

        } catch (error) {
            console.error(error);
        }
    }

    checkSMS();
    const smsInterval = setInterval(checkSMS, 5000);
}

document.querySelectorAll(".sms-session").forEach(initSmsPolling);


// ======================
// TOAST (for errors / success without reload)
// ======================

function showToast(message, type) {

    let wrap = document.querySelector(".sms-toast-wrap");

    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "sms-toast-wrap";
        document.body.appendChild(wrap);
    }

    const toast = document.createElement("div");
    toast.className = "sms-toast" + (type === "success" ? " sms-toast--success" : "");
    toast.innerText = message;

    wrap.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("show"));

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 4000);

}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}


// ======================
// INJECT NEW ORDER CARD (after successful AJAX request)
// ======================

function addOrderCard(order) {

    const container = document.querySelector(".sms-container");
    const cancelUrl = container ? container.dataset.cancelUrl : "";
    const csrfToken = container ? container.dataset.csrf : "";

    let wrap = document.querySelector(".sessions-wrap");

    // Create the sessions section if there were no active orders
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "sessions-wrap";
        container.appendChild(wrap);

        const title = document.createElement("h3");
        title.className = "sessions-title";
        title.innerHTML = '<span class="live-dot"></span> Active Numbers';
        wrap.appendChild(title);
    }

    const card = document.createElement("div");
    card.className = "sms-session";
    card.dataset.orderId = order.id;

    card.innerHTML = `

        <div class="sms-session-header">

            <span class="sms-country">
                ${escapeHtml(order.country_iso)}
            </span>

            <span class="sms-service">
                ${escapeHtml(order.service_name)}
            </span>

            <strong class="sms-timer" data-created="${escapeHtml(order.created_at)}">
                20:00
            </strong>

        </div>

        <div class="sms-session-item">

            <span>Number</span>

            <div class="sms-copy-box">

                <strong class="active-number">
                    ${escapeHtml(order.phone_number)}
                </strong>

                <button
                    type="button"
                    class="copy-btn"
                    data-copy="${escapeHtml(order.phone_number)}"
                    title="Copy Number">
                    <i class="fa-regular fa-copy"></i>
                </button>

            </div>

        </div>

        <div class="sms-session-item">

            <span>OTP</span>

            <div class="sms-copy-box">

                <div class="otp-box">Waiting...</div>

                <button
                    type="button"
                    class="copy-btn otp-copy-btn"
                    disabled
                    data-copy="">
                    <i class="fa-regular fa-copy"></i>
                </button>

            </div>

        </div>

        <div
            class="sms-session-item sms-status"
            data-provider-order="${escapeHtml(order.provider_order_id)}">

            <span class="waiting-pulse"><i class="fa-solid fa-spinner fa-spin"></i> Waiting for SMS...</span>

        </div>

        <form method="POST" action="${escapeHtml(cancelUrl)}" class="js-cancel-form">
            <input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(csrfToken)}">
            <input
                type="hidden"
                name="order_id"
                value="${order.id}">
            <button
                type="submit"
                class="sms-cancel-btn">
                Cancel Order
            </button>
        </form>

    `;

    // Insert right below the "Active Numbers" heading
    const title = wrap.querySelector(".sessions-title");
    if (title) {
        title.after(card);
    } else {
        wrap.prepend(card);
    }

    // Wire up timer, SMS polling and copy buttons for the new card
    const timer = card.querySelector(".sms-timer");
    if (timer) initCountdown(timer);
    initSmsPolling(card);
    initCopyButtons(card);

}


// ======================
// REQUEST NUMBER — AJAX (no page reload, no blank screen)
// ======================

const requestForm = document.getElementById("requestNumberForm");

if (requestForm) {

    requestForm.addEventListener("submit", async (e) => {

        e.preventDefault();

        const originalBtnContent = requestBtn.innerHTML;

        requestBtn.disabled = true;
        requestBtn.innerHTML =
            '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';

        try {

            const response = await fetch(
                requestForm.action || window.location.href,
                {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new FormData(requestForm),
                }
            );

            if (!response.ok) throw new Error("Server error");

            const data = await response.json();

            if (data.success && data.order) {

                addOrderCard(data.order);
                showToast(data.message, "success");

            } else if (data.redirect) {

                // Insufficient balance → go to wallet page as before.
                // Same-page redirect (warnings) → stay and just toast.
                const targetPath =
                    new URL(data.redirect, window.location.href).pathname;

                if (targetPath === window.location.pathname) {
                    showToast(data.message || "Please try again.");
                } else {
                    window.location.assign(data.redirect);
                    return;
                }

            } else {

                showToast(data.message || "Something went wrong. Please try again.");

            }

        } catch (error) {

            console.error(error);
            showToast("Network error. Please try again.");

        }

        requestBtn.disabled = false;
        requestBtn.innerHTML = originalBtnContent;

    });

}


// ======================
// PROCESSING OVERLAY
// Still used by the CANCEL forms until cancel goes AJAX (part 2).
// The request form no longer needs it.
// ======================

const smsOverlay = document.getElementById("smsOverlay");
const smsOverlayText = document.getElementById("smsOverlayText");

function showOverlay(message) {
    if (!smsOverlay) return;
    if (message && smsOverlayText) smsOverlayText.innerText = message;
    smsOverlay.hidden = false;
    document.body.style.overflow = "hidden";
}

document.querySelectorAll(".js-cancel-form")
.forEach(form => {

    form.addEventListener("submit", () => {

        showOverlay("Cancelling your order…");

    });

});

// Safety: never trap the user on the overlay
setTimeout(() => {
    if (smsOverlay) smsOverlay.hidden = true;
    document.body.style.overflow = "";
}, 45000);


// ======================
// SEARCHABLE DROPDOWNS
// ======================

document.addEventListener("DOMContentLoaded", () => {

    if (document.getElementById("serverSelect")) {
        new Choices("#serverSelect", {
            searchEnabled: false,
            itemSelectText: "",
            shouldSort: false,
            allowHTML: false
        });
    }

    if (document.getElementById("countrySelect")) {
        window.countryChoices = new Choices("#countrySelect", {
            searchEnabled: true,
            searchPlaceholderValue: "Search Country...",
            itemSelectText: "",
            shouldSort: false,
            allowHTML: false
        });
    }

    if (document.getElementById("serviceSelect")) {
        window.serviceChoices = new Choices("#serviceSelect", {
            searchEnabled: true,
            searchPlaceholderValue: "Search Service...",
            itemSelectText: "",
            shouldSort: false,
            allowHTML: false
        });
    }
});