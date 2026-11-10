/* ============================================================
   ABFverify - Referral Program & Code Redemption
   Handles: redeem floating modal, dashboard referral card,
   copy-to-clipboard buttons, battery progress animation.
   ============================================================ */
(function () {
    "use strict";

    /* ---------- CSRF ---------- */
    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }
    var csrftoken = getCookie("csrftoken");

    /* ---------- Toast helper (site-wide toast.js provides showToast) ---------- */
    function toast(level, text) {
        if (typeof window.showToast === "function") {
            window.showToast(level, text);
        } else {
            alert(text);
        }
    }

    /* ---------- Copy to clipboard ---------- */
    function copyText(text, btn) {
        function done() {
            if (btn) {
                var original = btn.innerHTML;
                btn.classList.add("copied");
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
                setTimeout(function () {
                    btn.classList.remove("copied");
                    btn.innerHTML = original;
                }, 1800);
            }
            toast("success", "Copied to clipboard!");
        }

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(done).catch(function () {
                legacyCopy(text);
                done();
            });
        } else {
            legacyCopy(text);
            done();
        }
    }

    function legacyCopy(text) {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try { document.execCommand("copy"); } catch (e) {}
        document.body.removeChild(ta);
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-copy]");
        if (!btn) return;
        e.preventDefault();
        copyText(btn.getAttribute("data-copy"), btn);
    });

    /* ============================================================
       REDEEM CODE MODAL
       ============================================================ */
    var redeemFloatBtn = document.getElementById("redeemFloatBtn");
    var redeemModal = document.getElementById("redeemModal");
    var redeemForm = document.getElementById("redeemForm");
    var redeemInput = document.getElementById("redeemCodeInput");
    var redeemSubmit = document.getElementById("redeemSubmitBtn");

    function openRedeem() {
        if (!redeemModal) return;
        redeemModal.classList.add("show");
        document.body.style.overflow = "hidden";
        if (redeemInput) {
            setTimeout(function () { redeemInput.focus(); }, 250);
        }
    }

    function closeRedeem() {
        if (!redeemModal) return;
        redeemModal.classList.remove("show");
        document.body.style.overflow = "";
    }

    if (redeemFloatBtn) {
        redeemFloatBtn.addEventListener("click", openRedeem);
    }

    if (redeemModal) {
        redeemModal.addEventListener("click", function (e) {
            if (e.target === redeemModal || e.target.closest("[data-redeem-close]")) {
                closeRedeem();
            }
        });
    }

    if (redeemForm) {
        redeemForm.addEventListener("submit", function (e) {
            e.preventDefault();

            var code = redeemInput ? redeemInput.value.trim() : "";
            if (!code) {
                toast("error", "Please enter a code.");
                return;
            }

            if (redeemSubmit) {
                redeemSubmit.disabled = true;
                redeemSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Redeeming...';
            }

            var formData = new FormData();
            formData.append("code", code);

            fetch(redeemForm.action, {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken },
                body: formData,
                credentials: "same-origin"
            })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.success) {
                        var amount = Number(data.amount).toLocaleString("en-NG", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        });
                        toast("success", "Code redeemed! \u20a6" + amount + " credited to your wallet.");

                        /* Update the topbar wallet balance instantly */
                        if (data.new_balance) {
                            var walletEl = document.querySelector(".topbar-user .wallet");
                            if (walletEl) {
                                walletEl.textContent = "\u20a6" + Number(data.new_balance).toLocaleString("en-NG", {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2
                                });
                            }
                        }

                        if (redeemInput) redeemInput.value = "";
                        closeRedeem();
                    } else {
                        toast("error", data.error || "Could not redeem this code.");
                    }
                })
                .catch(function () {
                    toast("error", "Network error. Please try again.");
                })
                .finally(function () {
                    if (redeemSubmit) {
                        redeemSubmit.disabled = false;
                        redeemSubmit.innerHTML = '<i class="fa-solid fa-gift"></i> Redeem Code';
                    }
                });
        });
    }

    /* ============================================================
       DASHBOARD REFERRAL CARD (re-shows every 6 hours)
       ============================================================ */
    var refCard = document.getElementById("referralCardModal");

    if (refCard) {
        /* Slight delay so it feels intentional, not jumpy */
        setTimeout(function () {
            refCard.classList.add("show");
            document.body.style.overflow = "hidden";
        }, 700);

        function dismissCard(postToServer) {
            refCard.classList.remove("show");
            document.body.style.overflow = "";
            if (postToServer && refCard.getAttribute("data-dismiss-url")) {
                fetch(refCard.getAttribute("data-dismiss-url"), {
                    method: "POST",
                    headers: { "X-CSRFToken": csrftoken },
                    credentials: "same-origin"
                }).catch(function () { /* silent - card will just show again */ });
            }
        }

        refCard.addEventListener("click", function (e) {
            if (e.target.closest("[data-ref-dismiss]")) {
                e.preventDefault();
                dismissCard(true);
            } else if (e.target === refCard) {
                dismissCard(true); /* tapping the backdrop counts as dismissal */
            }
        });
    }

    /* ============================================================
       BATTERY PROGRESS BARS (settings page)
       ============================================================ */
    function animateBatteries() {
        document.querySelectorAll(".ref-battery-fill").forEach(function (fill) {
            var pct = parseInt(fill.getAttribute("data-progress") || "0", 10);
            pct = Math.max(0, Math.min(100, pct));
            requestAnimationFrame(function () {
                setTimeout(function () {
                    fill.style.width = pct + "%";
                }, 300);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", animateBatteries);
    } else {
        animateBatteries();
    }

    /* Close any open referral modal with Escape */
    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        if (redeemModal && redeemModal.classList.contains("show")) {
            closeRedeem();
        }
        if (refCard && refCard.classList.contains("show")) {
            refCard.classList.remove("show");
            document.body.style.overflow = "";
        }
    });
})();
