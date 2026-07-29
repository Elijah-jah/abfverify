function getCookie(name) {

    let cookieValue = null;

    if (document.cookie && document.cookie !== "") {

        const cookies = document.cookie.split(";");

        for (let i = 0; i < cookies.length; i++) {

            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === (name + "=")) {

                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );

                break;
            }
        }
    }

    return cookieValue;
}




// ==============================
// QUICK AMOUNT BUTTONS
// ==============================

const amountInput = document.getElementById("amountInput");

const chips = document.querySelectorAll(".wallet-chip");


chips.forEach(chip => {

    chip.addEventListener("click", function () {

        amountInput.value = this.dataset.amount;

    });

});




// ==============================
// FUND WALLET
// ==============================

const fundButton = document.getElementById("fundButton");

// Extra safeguard against multiple requests
let paymentProcessing = false;

fundButton.addEventListener("click", function () {

    // Ignore if already processing
    if (paymentProcessing || fundButton.disabled) {
        return;
    }

    const amount = Number(amountInput.value);

    // Minimum deposit validation
    if (!amount || amount < 500) {

        if (typeof showToast === "function") {
            showToast("warning", "Minimum deposit is ₦500.");
        } else {
            console.error("showToast is not available");
            alert("Minimum deposit is ₦500.");
        }

        return;
    }

    // Lock the button immediately
    paymentProcessing = true;
    fundButton.disabled = true;
    fundButton.textContent = "Redirecting...";

    fetch("/wallet/fund/", {

        method: "POST",

        headers: {

            "Content-Type": "application/x-www-form-urlencoded",

            "X-CSRFToken": getCookie("csrftoken")

        },

        body: new URLSearchParams({

            amount: amount

        })

    })

    .then(response => response.json())

    .then(data => {

        console.log(data);

        if (data.payment_url) {

            // Redirect immediately
            window.location.href = data.payment_url;

        } else {

            paymentProcessing = false;
            fundButton.disabled = false;
            fundButton.textContent = "Proceed to Payment";

            if (typeof showToast === "function") {
                showToast("error", data.error || "Unable to initialize payment.");
            } else {
                console.error("showToast is not available");
                alert(data.error || "Unable to initialize payment.");
            }

        }

    })

    .catch(error => {

        console.error(error);

        paymentProcessing = false;
        fundButton.disabled = false;
        fundButton.textContent = "Proceed to Payment";

        if (typeof showToast === "function") {
            showToast("error", "Unable to connect. Please try again.");
        } else {
            console.error("showToast is not available");
            alert("Unable to connect. Please try again.");
        }

    });

});