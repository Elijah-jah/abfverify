/* =========================================================
   ABFverify — Gift Sending (customer page)
   Category filter, order form modal, client-side photo
   compression, confirm dialog, wallet-charge submit, success.
   ========================================================= */
(function () {
    "use strict";

    var MAX_IMAGES = 5;
    var MAX_DIMENSION = 2000;   // px, longest side
    var JPEG_QUALITY = 0.85;    // visually lossless for web viewing

    /* ---------------- Search + category pill filter ---------------- */
    var pills = document.querySelectorAll(".gf-pill");
    var cards = document.querySelectorAll(".gf-card");
    var emptyCat = document.getElementById("gfEmptyCat");
    var searchInput = document.getElementById("gfSearch");
    var searchClear = document.getElementById("gfSearchClear");
    var activeCat = "all";

    function applyFilters() {
        var query = (searchInput ? searchInput.value : "").trim().toLowerCase();
        var visible = 0;

        cards.forEach(function (card) {
            var inCat = activeCat === "all" || card.getAttribute("data-cat") === activeCat;
            var haystack = card.getAttribute("data-search") || "";
            var matches = !query || haystack.indexOf(query) !== -1;
            var show = inCat && matches;
            card.classList.toggle("gf-hidden", !show);
            if (show) visible++;
        });

        if (emptyCat) {
            emptyCat.classList.toggle("gf-hidden", visible > 0);
            var msg = emptyCat.querySelector("p");
            if (msg) {
                msg.textContent = query
                    ? "No gifts match \"" + searchInput.value.trim() + "\" in this section."
                    : "No gifts available in this category yet.";
            }
        }
        if (searchClear) {
            searchClear.classList.toggle("gf-hidden", query.length === 0);
        }
    }

    pills.forEach(function (pill) {
        pill.addEventListener("click", function () {
            pills.forEach(function (p) {
                p.classList.remove("active");
                p.setAttribute("aria-selected", "false");
            });
            pill.classList.add("active");
            pill.setAttribute("aria-selected", "true");
            activeCat = pill.getAttribute("data-cat");
            applyFilters();
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
        searchInput.addEventListener("search", applyFilters); // native clear (x) on some browsers
    }
    if (searchClear) {
        searchClear.addEventListener("click", function () {
            searchInput.value = "";
            applyFilters();
            searchInput.focus();
        });
    }

    /* ---------------- Modal helpers ---------------- */
    function openOverlay(el) {
        el.classList.add("open");
        el.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
    }

    function closeOverlay(el) {
        el.classList.remove("open");
        el.setAttribute("aria-hidden", "true");
        if (!document.querySelector(".gf-modal-overlay.open")) {
            document.body.style.overflow = "";
        }
    }

    var formModal = document.getElementById("gfFormModal");
    var sureModal = document.getElementById("gfSureModal");
    var successModal = document.getElementById("gfSuccessModal");
    var detailModal = document.getElementById("gfDetailModal");

    if (!formModal) return; // not on the gift sending page

    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        [sureModal, successModal, formModal, detailModal].forEach(function (m) {
            if (m && m.classList.contains("open")) closeOverlay(m);
        });
    });

    [formModal, sureModal, successModal, detailModal].forEach(function (m) {
        if (!m) return;
        m.addEventListener("click", function (e) {
            if (e.target === m) closeOverlay(m);
        });
    });

    /* ---------------- Current selection state ---------------- */
    var current = {
        groupId: null,
        name: "",
        price: "0.00",
        orderUrl: ""
    };
    var chosenFiles = []; // compressed File/Blob objects, max 5

    var form = document.getElementById("gfOrderForm");
    var formError = document.getElementById("gfFormError");
    var confirmBtn = document.getElementById("gfConfirmBtn");

    /* ---------------- Open the order form (from any trigger) ---------------- */
    function openGiftForm(data) {
        current.groupId = data.id;
        current.name = data.name || "Gift";
        current.price = data.price || "0.00";
        current.orderUrl = data.orderUrl;

        document.getElementById("gfModalTitle").textContent = current.name;
        document.getElementById("gfModalPrice").textContent = "₦" + fmt(current.price);
        document.getElementById("gfConfirmPrice").textContent = "₦" + fmt(current.price);

        var durEl = document.getElementById("gfModalDuration");
        durEl.textContent = data.duration ? "Delivery: " + data.duration : "";

        var img = document.getElementById("gfModalImg");
        var fallback = document.getElementById("gfModalImgFallback");
        if (data.image) {
            img.src = data.image;
            img.style.display = "block";
            fallback.style.display = "none";
        } else {
            img.style.display = "none";
            fallback.style.display = "flex";
        }

        form.reset();
        clearImages();
        clearErrors();
        openOverlay(formModal);
    }

    function cardData(el) {
        return {
            id: el.getAttribute("data-group-id"),
            name: el.getAttribute("data-group-name"),
            cat: el.getAttribute("data-cat-name") || "",
            desc: el.getAttribute("data-group-desc") || "",
            price: el.getAttribute("data-group-price"),
            image: el.getAttribute("data-group-image") || "",
            duration: el.getAttribute("data-group-duration") || "",
            orderUrl: el.getAttribute("data-order-url")
        };
    }

    document.querySelectorAll(".js-open-gift").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.stopPropagation(); // don't bubble into the card's detail-view handler
            openGiftForm(cardData(btn));
        });
    });

    /* ---------------- Product details popup (tap the card) ---------------- */
    var detailData = null;

    function openGiftDetail(data) {
        detailData = data;

        document.getElementById("gfDetailName").textContent = data.name || "Gift";
        document.getElementById("gfDetailCat").textContent = data.cat || "";
        document.getElementById("gfDetailPrice").textContent = "₦" + fmt(data.price);

        var descEl = document.getElementById("gfDetailDesc");
        descEl.textContent = data.desc || "";
        descEl.classList.toggle("gf-hidden", !data.desc);

        var durBadge = document.getElementById("gfDetailDurationBadge");
        document.getElementById("gfDetailDurationText").textContent = data.duration || "";
        durBadge.classList.toggle("gf-hidden", !data.duration);

        var wrap = document.getElementById("gfDetailImgWrap");
        var img = document.getElementById("gfDetailImg");
        var fallback = document.getElementById("gfDetailImgFallback");
        if (data.image) {
            img.src = data.image;
            img.style.display = "block";
            fallback.style.display = "none";
            wrap.style.setProperty("--gf-img", "url('" + data.image + "')");
        } else {
            img.style.display = "none";
            fallback.style.display = "flex";
            wrap.style.removeProperty("--gf-img");
        }

        openOverlay(detailModal);
    }

    document.querySelectorAll(".js-view-gift").forEach(function (card) {
        card.addEventListener("click", function () {
            openGiftDetail(cardData(card));
        });
        card.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openGiftDetail(cardData(card));
            }
        });
    });

    document.querySelectorAll(".js-close-detail").forEach(function (btn) {
        btn.addEventListener("click", function () { closeOverlay(detailModal); });
    });

    document.getElementById("gfDetailSend").addEventListener("click", function () {
        if (!detailData) return;
        closeOverlay(detailModal);
        openGiftForm(detailData);
    });

    document.querySelectorAll(".js-close-modal").forEach(function (btn) {
        btn.addEventListener("click", function () { closeOverlay(formModal); });
    });

    /* ---------------- Image picking + compression ---------------- */
    var fileInput = document.getElementById("gfImages");
    var pickBtn = document.getElementById("gfPickImages");
    var previews = document.getElementById("gfPreviews");
    var countEl = document.getElementById("gfImageCount");
    var imagesError = document.getElementById("gfImagesError");

    pickBtn.addEventListener("click", function () { fileInput.click(); });

    fileInput.addEventListener("change", function () {
        var files = Array.prototype.slice.call(fileInput.files || []);
        imagesError.textContent = "";

        files.forEach(function (file) {
            if (chosenFiles.length >= MAX_IMAGES) {
                imagesError.textContent = "You can attach at most " + MAX_IMAGES + " photos.";
                return;
            }
            if (!/^image\//.test(file.type)) {
                imagesError.textContent = file.name + " is not an image.";
                return;
            }
            compressImage(file).then(function (blob) {
                chosenFiles.push(blob);
                renderPreviews();
            }).catch(function () {
                imagesError.textContent = "Could not read " + file.name + ".";
            });
        });

        fileInput.value = ""; // allow picking the same file again
    });

    function compressImage(file) {
        return new Promise(function (resolve, reject) {
            var url = URL.createObjectURL(file);
            var img = new Image();
            img.onload = function () {
                URL.revokeObjectURL(url);
                var w = img.naturalWidth;
                var h = img.naturalHeight;
                var scale = Math.min(1, MAX_DIMENSION / Math.max(w, h));
                w = Math.max(1, Math.round(w * scale));
                h = Math.max(1, Math.round(h * scale));

                var canvas = document.createElement("canvas");
                canvas.width = w;
                canvas.height = h;
                var ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, w, h);

                canvas.toBlob(function (blob) {
                    if (!blob) { reject(new Error("compress failed")); return; }
                    // Keep the original type when it is already efficient,
                    // otherwise store as high-quality JPEG.
                    var keep = /image\/(jpeg|webp)/.test(file.type) && blob.size > file.size;
                    resolve(keep ? file : blob);
                }, "image/jpeg", JPEG_QUALITY);
            };
            img.onerror = function () {
                URL.revokeObjectURL(url);
                reject(new Error("bad image"));
            };
            img.src = url;
        });
    }

    function renderPreviews() {
        previews.innerHTML = "";
        chosenFiles.forEach(function (blob, idx) {
            var wrap = document.createElement("div");
            wrap.className = "gf-preview";

            var img = document.createElement("img");
            img.src = URL.createObjectURL(blob);
            img.alt = "Photo " + (idx + 1);

            var rm = document.createElement("button");
            rm.type = "button";
            rm.className = "gf-preview-remove";
            rm.setAttribute("aria-label", "Remove photo");
            rm.innerHTML = '<i class="fa-solid fa-xmark"></i>';
            rm.addEventListener("click", function () {
                chosenFiles.splice(idx, 1);
                renderPreviews();
            });

            wrap.appendChild(img);
            wrap.appendChild(rm);
            previews.appendChild(wrap);
        });
        countEl.textContent = chosenFiles.length + " / " + MAX_IMAGES;
    }

    function clearImages() {
        chosenFiles = [];
        renderPreviews();
        imagesError.textContent = "";
    }

    /* ---------------- Validation ---------------- */
    var REQUIRED = ["sender_name", "receiver_name", "address", "city", "state", "zip_code", "phone"];

    function clearErrors() {
        formError.textContent = "";
        form.querySelectorAll(".gf-invalid").forEach(function (el) {
            el.classList.remove("gf-invalid");
        });
    }

    function validate() {
        clearErrors();
        var ok = true;
        REQUIRED.forEach(function (name) {
            var field = form.elements[name];
            if (field && !field.value.trim()) {
                field.classList.add("gf-invalid");
                ok = false;
            }
        });
        if (!ok) formError.textContent = "Please fill in every delivery field above.";
        return ok;
    }

    /* ---------------- Confirm flow ---------------- */
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!validate()) return;

        document.getElementById("gfSureGift").textContent = current.name;
        document.getElementById("gfSurePrice").textContent = "₦" + fmt(current.price);
        openOverlay(sureModal);
    });

    document.getElementById("gfSureNo").addEventListener("click", function () {
        closeOverlay(sureModal);
    });

    document.getElementById("gfSureYes").addEventListener("click", function () {
        closeOverlay(sureModal);
        submitOrder();
    });

    function submitOrder() {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending…';
        formError.textContent = "";

        var fd = new FormData(form); // includes csrfmiddlewaretoken
        chosenFiles.forEach(function (blob, idx) {
            var name = blob.name || ("photo_" + (idx + 1) + ".jpg");
            fd.append("images", blob, name);
        });

        fetch(current.orderUrl, {
            method: "POST",
            body: fd,
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
            .then(function (res) {
                return res.json().then(function (data) {
                    return { ok: res.ok, data: data };
                }).catch(function () {
                    return { ok: false, data: { error: "Unexpected server response. Please try again." } };
                });
            })
            .then(function (result) {
                if (result.ok && result.data.success) {
                    closeOverlay(formModal);
                    showSuccess(result.data);
                } else {
                    handleFailure(result.data);
                }
            })
            .catch(function () {
                formError.textContent = "Network problem. Please check your connection and try again.";
            })
            .finally(function () {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Confirm Sending — <span id="gfConfirmPrice">₦' + fmt(current.price) + "</span>";
            });
    }

    function handleFailure(data) {
        var msg = (data && data.error) || "Could not place your order. Please try again.";
        formError.textContent = msg;

        if (data && data.errors) {
            Object.keys(data.errors).forEach(function (field) {
                var el = form.elements[field];
                if (el) el.classList.add("gf-invalid");
            });
        }

        // Refresh the balance pill if the server says the wallet is short —
        // the message already tells the user what happened.
    }

    /* ---------------- Success ---------------- */
    function showSuccess(data) {
        document.getElementById("gfSuccessOrder").textContent = data.order_id || "—";
        document.getElementById("gfSuccessGift").textContent = data.group_name || current.name;
        document.getElementById("gfSuccessPrice").textContent = "₦" + fmt(data.price || current.price);
        document.getElementById("gfSuccessBalance").textContent = "₦" + fmt(data.new_balance || "0");

        // Live-update the wallet pills so the user sees the deduction.
        if (data.new_balance != null) {
            var pretty = "₦" + fmt(data.new_balance);
            document.querySelectorAll(".gf-wallet-pill span").forEach(function (el) {
                el.textContent = pretty;
            });
            var topbarWallet = document.querySelector(".topbar .wallet");
            if (topbarWallet) topbarWallet.textContent = pretty;
        }

        openOverlay(successModal);
    }

    document.getElementById("gfSuccessStay").addEventListener("click", function () {
        closeOverlay(successModal);
    });

    /* ---------------- Utils ---------------- */
    function fmt(num) {
        var n = parseFloat(num);
        if (isNaN(n)) n = 0;
        return n.toLocaleString("en-NG", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
})();
