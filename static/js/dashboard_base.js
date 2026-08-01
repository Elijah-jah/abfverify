console.log("dashboard_base.js loaded");


// =============================
// SIDEBAR
// =============================

const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");
const hamburger = document.getElementById("hamburger");

if (hamburger && sidebar && overlay) {

    hamburger.addEventListener("click", function () {

        sidebar.classList.add("active");
        overlay.classList.add("active");

    });


    overlay.addEventListener("click", function () {

        sidebar.classList.remove("active");
        overlay.classList.remove("active");

    });

}


// =============================
// THEME TOGGLE
// =============================

const themeToggle = document.getElementById("themeToggle");


// =============================
// SET THEME
// =============================

function setTheme(isLight) {

    // Remove previous theme classes
    document.body.classList.remove("light", "dark");


    // Apply selected theme
    if (isLight) {

        document.body.classList.add("light");

    } else {

        document.body.classList.add("dark");

    }


    // Update theme button
    if (themeToggle) {

        if (isLight) {

            themeToggle.innerHTML =
                '<i class="fa-solid fa-moon"></i>' +
                '<span>Dark Mode</span>';

        } else {

            themeToggle.innerHTML =
                '<i class="fa-solid fa-sun"></i>' +
                '<span>Light Mode</span>';

        }

    }


    // Save theme
    localStorage.setItem(
        "theme",
        isLight ? "light" : "dark"
    );

}


// =============================
// LOAD SAVED THEME
// =============================

const savedTheme = localStorage.getItem("theme");


if (savedTheme === "light") {

    setTheme(true);

} else if (savedTheme === "dark") {

    setTheme(false);

} else {

    // Default theme
    setTheme(true);

}


// =============================
// TOGGLE THEME
// =============================

if (themeToggle) {

    themeToggle.addEventListener("click", function () {

        const isCurrentlyLight =
            document.body.classList.contains("light");


        // Switch to opposite theme
        setTheme(!isCurrentlyLight);

    });

}


// =============================
// LOGOUT MODAL
// =============================

document.addEventListener("DOMContentLoaded", function () {


    const logoutButtons =
        document.querySelectorAll(".logout-trigger");


    const logoutModal =
        document.getElementById("logoutModal");


    const cancelLogout =
        document.getElementById("cancelLogout");


    if (!logoutModal || !cancelLogout) {

        return;

    }


    // =============================
    // OPEN MODAL
    // =============================

    function openLogoutModal() {

        logoutModal.classList.add("show");

        document.body.style.overflow = "hidden";

    }


    // =============================
    // CLOSE MODAL
    // =============================

    function closeLogoutModal() {

        logoutModal.classList.remove("show");

        document.body.style.overflow = "";

    }


    // =============================
    // LOGOUT BUTTONS
    // =============================

    logoutButtons.forEach(function (button) {

        button.addEventListener("click", function (e) {

            e.preventDefault();

            openLogoutModal();

        });

    });


    // =============================
    // CANCEL LOGOUT
    // =============================

    cancelLogout.addEventListener(
        "click",
        function () {

            closeLogoutModal();

        }
    );


    // =============================
    // CLICK OUTSIDE MODAL
    // =============================

    logoutModal.addEventListener(
        "click",
        function (e) {

            if (e.target === logoutModal) {

                closeLogoutModal();

            }

        }
    );


    // =============================
    // ESC KEY
    // =============================

    document.addEventListener(
        "keydown",
        function (e) {

            if (
                e.key === "Escape" &&
                logoutModal.classList.contains("show")
            ) {

                closeLogoutModal();

            }

        }
    );

});


// Show notice modal on load
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('noticeModal');
    const btnGotIt = document.getElementById('btnGotIt');
    
    if (!modal) return;
    
    // Check if user already dismissed this session
    if (!sessionStorage.getItem('noticeDismissed')) {
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'none';
    }
    
    // Dismiss button
    if (btnGotIt) {
        btnGotIt.addEventListener('click', function() {
            modal.style.display = 'none';
            sessionStorage.setItem('noticeDismissed', 'true');
        });
    }
});