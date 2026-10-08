document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    /* ==========================
       SHOW / HIDE PASSWORD
    ========================== */

    document.querySelectorAll(".cp-toggle").forEach(function (button) {

        button.addEventListener("click", function () {

            var input = document.getElementById(this.getAttribute("data-target"));
            var icon = this.querySelector("i");

            if (!input || !icon) return;

            var show = input.type === "password";

            input.type = show ? "text" : "password";
            icon.classList.toggle("fa-eye", !show);
            icon.classList.toggle("fa-eye-slash", show);

        });

    });


    /* ==========================
       CHANGE PASSWORD VALIDATION
    ========================== */

    var form = document.getElementById("changePasswordForm");

    if (form) {

        form.addEventListener("submit", function (e) {

            var currentPassword = document.getElementById("currentPassword").value.trim();
            var newPassword = document.getElementById("newPassword").value;
            var confirmPassword = document.getElementById("confirmPassword").value;

            if (!currentPassword) {
                e.preventDefault();
                showToast("warning", "Please enter your current password.");
                return;
            }

            if (!newPassword) {
                e.preventDefault();
                showToast("warning", "Please enter your new password.");
                return;
            }

            if (currentPassword === newPassword) {
                e.preventDefault();
                showToast("error", "New password cannot be the same as your current password.");
                return;
            }

            if (newPassword !== confirmPassword) {
                e.preventDefault();
                showToast("error", "New passwords do not match.");
                return;
            }

            showToast("success", "Password is being updated...");

        });

    }

});