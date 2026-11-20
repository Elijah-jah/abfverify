/* =========================================================
   ABFverify — Dashboard Base JS  (Redesigned)
   Sidebar / theme / logout modal / notice modal
========================================================= */

(function () {
    "use strict";

    /* =============================
       SIDEBAR
    ============================= */

    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const hamburger = document.getElementById("hamburger");

    function openSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.add("active");
        overlay.classList.add("active");
    }

    function closeSidebar() {
        if (!sidebar || !overlay) return;
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
    }

    if (hamburger) {
        hamburger.addEventListener("click", openSidebar);
    }

    if (overlay) {
        overlay.addEventListener("click", closeSidebar);
    }


    /* =============================
       THEME TOGGLE
    ============================= */

    const themeToggle = document.getElementById("themeToggle");

    function setTheme(isLight) {

        document.body.classList.remove("light", "dark");
        document.body.classList.add(isLight ? "light" : "dark");

        if (themeToggle) {
            themeToggle.innerHTML = isLight
                ? '<i class="fa-solid fa-moon"></i><span>Dark Mode</span>'
                : '<i class="fa-solid fa-sun"></i><span>Light Mode</span>';
        }

        localStorage.setItem("theme", isLight ? "light" : "dark");
    }

    // Initial theme: saved preference > system preference > light
    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "light" || savedTheme === "dark") {
        setTheme(savedTheme === "light");
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
        setTheme(false);
    } else {
        setTheme(true);
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const isCurrentlyLight = document.body.classList.contains("light");
            setTheme(!isCurrentlyLight);
        });
    }


    /* =============================
       LOGOUT MODAL
    ============================= */

    document.addEventListener("DOMContentLoaded", function () {

        const logoutButtons = document.querySelectorAll(".logout-trigger");
        const logoutModal = document.getElementById("logoutModal");
        const cancelLogout = document.getElementById("cancelLogout");

        if (!logoutModal || !cancelLogout) return;

        function openLogoutModal() {
            logoutModal.classList.add("show");
            document.body.style.overflow = "hidden";
        }

        function closeLogoutModal() {
            logoutModal.classList.remove("show");
            document.body.style.overflow = "";
        }

        logoutButtons.forEach(function (button) {
            button.addEventListener("click", function (e) {
                e.preventDefault();
                openLogoutModal();
            });
        });

        cancelLogout.addEventListener("click", closeLogoutModal);

        logoutModal.addEventListener("click", function (e) {
            if (e.target === logoutModal) closeLogoutModal();
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && logoutModal.classList.contains("show")) {
                closeLogoutModal();
            }
        });
    });


    /* =============================
       NOTICE MODAL (session dismiss)
    ============================= */

    document.addEventListener("DOMContentLoaded", function () {
        const modal = document.getElementById("noticeModal");
        const btnGotIt = document.getElementById("btnGotIt");

        if (!modal) return;

        if (!sessionStorage.getItem("noticeDismissed")) {
            modal.style.display = "flex";
        } else {
            modal.style.display = "none";
        }

        if (btnGotIt) {
            btnGotIt.addEventListener("click", function () {
                modal.style.display = "none";
                sessionStorage.setItem("noticeDismissed", "true");
            });
        }
    });

})();