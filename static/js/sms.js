const countrySelect = document.getElementById("countrySelect");
const serviceSelect = document.getElementById("serviceSelect");
const serverSelect = document.getElementById("serverSelect");
const priceDisplay = document.getElementById("priceDisplay");
const stockDisplay = document.getElementById("stockDisplay");
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
        stockDisplay.innerText = "--";
        requestBtn.disabled = true;
        
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
        // Calls /api/get-price/ which reads from database cache (INSTANT)
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


// ======================
// UPDATE STOCK (LIVE - WITH PROPER LOADING & ERROR STATES)
// ======================

async function updateStock() {
    const country = countrySelect.value;
    const service = serviceSelect.value;
    const server = serverSelect ? serverSelect.value : "server3";

    if (!country || !service) {
        stockDisplay.innerText = "--";
        requestBtn.disabled = true;
        return;
    }

    // Show "Checking..." while waiting — NOT "Out of Stock"
    stockDisplay.innerText = "Checking...";
    requestBtn.disabled = true;

    try {
        const response = await fetch(
            `/api/check-stock/?country=${country}&service=${service}&server=${server}`
        );

        const data = await response.json();

        if (data.success === false) {
            // API error (timeout, connection issue, provider down)
            stockDisplay.innerText = "Check failed";
            requestBtn.disabled = true;
        } else if (data.available > 0) {
            // In stock
            stockDisplay.innerText = `${data.available} Available`;
            requestBtn.disabled = false;
        } else {
            // Genuinely out of stock
            stockDisplay.innerText = "Out of Stock";
            requestBtn.disabled = true;
        }

    } catch (error) {
        console.error(error);
        stockDisplay.innerText = "Unavailable";
        requestBtn.disabled = true;
    }
}


// Only update price/stock when BOTH country and service are selected
if (countrySelect && serviceSelect) {
    countrySelect.addEventListener("change", () => {
        if (serviceSelect.value) {
            updatePrice();
            updateStock();
        }
    });

    serviceSelect.addEventListener("change", () => {
        if (countrySelect.value) {
            updatePrice();
            updateStock();
        }
    });
}


// ======================
// COUNTDOWN TIMERS
// ======================

document.querySelectorAll(".sms-timer").forEach(timer => {

    const createdAt = timer.dataset.created;
    const session = timer.closest(".sms-session");

    console.log("Timer found, created:", createdAt, "session:", session);

    if (!createdAt || !session) {
        console.log("Missing createdAt or session, hiding container");
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

});


// ======================
// COPY BUTTONS
// ======================

document.querySelectorAll(".copy-btn")
.forEach(button => {

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


// ======================
// AUTO CHECK SMS
// ======================

document.querySelectorAll(".sms-session").forEach(session => {

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
});


// ======================
// PREVENT DOUBLE CLICK
// ======================

const requestForm =
    document.getElementById("requestNumberForm");

if (requestForm) {

    requestForm.addEventListener("submit", () => {

        requestBtn.disabled = true;

        requestBtn.innerText =
            "Processing...";

    });

}


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