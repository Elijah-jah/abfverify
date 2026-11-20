/* =========================================================
   ABFverify — My Gift Orders (customer page)
   Order detail modal with tracking link.
   ========================================================= */
(function () {
    "use strict";

    var modal = document.getElementById("gfOrderModal");
    if (!modal) return;

    function openOverlay(el) {
        el.classList.add("open");
        el.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
    }

    function closeOverlay(el) {
        el.classList.remove("open");
        el.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    document.querySelectorAll(".js-close-order").forEach(function (btn) {
        btn.addEventListener("click", function () { closeOverlay(modal); });
    });

    modal.addEventListener("click", function (e) {
        if (e.target === modal) closeOverlay(modal);
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal.classList.contains("open")) {
            closeOverlay(modal);
        }
    });

    var STATUS_LABELS = {
        pending: "Pending",
        processing: "Processing",
        completed: "Completed"
    };

    document.querySelectorAll(".js-view-order").forEach(function (row) {
        row.addEventListener("click", function () {
            var data;
            try {
                data = JSON.parse(row.getAttribute("data-order"));
            } catch (err) {
                return;
            }

            document.getElementById("gfOrderId").textContent = data.order_id || "";
            document.getElementById("gfOrderModalTitle").textContent = data.group_name || "Gift";
            document.getElementById("gfOrderPrice").textContent = "₦" + fmt(data.price);

            var status = document.getElementById("gfOrderStatus");
            status.textContent = STATUS_LABELS[data.status] || data.status || "Pending";
            status.className = "gf-status gf-status-" + (data.status || "pending");

            var img = document.getElementById("gfOrderImg");
            var fallback = document.getElementById("gfOrderImgFallback");
            if (data.group_image_url) {
                img.src = data.group_image_url;
                img.style.display = "block";
                fallback.style.display = "none";
            } else {
                img.style.display = "none";
                fallback.style.display = "flex";
            }

            document.getElementById("gfDetailSender").textContent = data.sender_name || "—";
            document.getElementById("gfDetailReceiver").textContent = data.receiver_name || "—";
            document.getElementById("gfDetailAddress").textContent = data.address || "—";
            document.getElementById("gfDetailCity").textContent = data.city || "—";
            document.getElementById("gfDetailState").textContent = data.state || "—";
            document.getElementById("gfDetailZip").textContent = data.zip_code || "—";
            document.getElementById("gfDetailPhone").textContent = data.phone || "—";
            document.getElementById("gfDetailCreated").textContent = data.created || "—";

            // Tracking link
            var link = document.getElementById("gfTrackingLink");
            var wait = document.getElementById("gfTrackingWait");
            if (data.tracking_link) {
                link.style.display = "inline-flex";
                link.href = data.tracking_link;
                link.textContent = "";
                link.appendChild(document.createTextNode("Track your gift"));
                var icon = document.createElement("i");
                icon.className = "fa-solid fa-arrow-up-right-from-square";
                link.appendChild(icon);
                wait.style.display = "none";
            } else {
                link.style.display = "none";
                wait.style.display = "block";
            }

            // Photos
            var photosWrap = document.getElementById("gfOrderPhotosWrap");
            var photos = document.getElementById("gfOrderPhotos");
            photos.innerHTML = "";
            if (data.images && data.images.length) {
                photosWrap.classList.remove("gf-hidden");
                data.images.forEach(function (url) {
                    var a = document.createElement("a");
                    a.href = url;
                    // base target="_blank" already opens these in a new tab.
                    var im = document.createElement("img");
                    im.src = url;
                    im.alt = "Attached photo";
                    im.loading = "lazy";
                    a.appendChild(im);
                    photos.appendChild(a);
                });
            } else {
                photosWrap.classList.add("gf-hidden");
            }

            openOverlay(modal);
        });
    });

    function fmt(num) {
        var n = parseFloat(num);
        if (isNaN(n)) n = 0;
        return n.toLocaleString("en-NG", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
})();
