document.addEventListener("DOMContentLoaded", function () {

    

    // ==========================
    // BACK TO TOP BUTTON
    // ==========================

    const backTop =
        document.getElementById("backToTop");

    if (backTop) {

        window.addEventListener("scroll", function () {

            if (window.scrollY > 400) {

                backTop.classList.add("show");

            } else {

                backTop.classList.remove("show");

            }

        });

        backTop.addEventListener("click", function () {

            window.scrollTo({

                top: 0,

                behavior: "smooth"

            });

        });

    }

    // ==========================
    // SCROLL ANIMATION
    // ==========================

    const animatedElements = document.querySelectorAll(
        ".feature-card, .step-card, .offer-card, .stat-box, .hero-title, .hero-description, .hero-buttons"
    );

    const observer = new IntersectionObserver(

        (entries) => {

            entries.forEach((entry) => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("animate");

                }

            });

        },

        {

            threshold: 0.15

        }

    );

    animatedElements.forEach((element) => {

        observer.observe(element);

    });

    // ==========================
    // ACTIVE NAV LINK
    // ==========================

    const sections =
        document.querySelectorAll("section[id]");

    const navLinks =
        document.querySelectorAll(".nav-link");

    window.addEventListener("scroll", function () {

        let current = "";

        sections.forEach((section) => {

            const sectionTop =
                section.offsetTop - 120;

            if (window.scrollY >= sectionTop) {

                current = section.getAttribute("id");

            }

        });

        navLinks.forEach((link) => {

            link.classList.remove("active");

            if (

                link.getAttribute("href") === "#" + current

            ) {

                link.classList.add("active");

            }

        });

    });

    // ==========================
    // PHONE FLOAT EFFECT
    // ==========================

    const phone =
        document.querySelector(".phone-frame");

    if (phone) {

        window.addEventListener("mousemove", function (e) {

            const x =
                (window.innerWidth / 2 - e.clientX) / 80;

            const y =
                (window.innerHeight / 2 - e.clientY) / 80;

            phone.style.transform =
                `rotateY(${x}deg) rotateX(${-y}deg)`;

        });

        window.addEventListener("mouseleave", function () {

            phone.style.transform =
                "rotateY(0deg) rotateX(0deg)";

        });

    }

});


// ==========================
    // THEME TOGGLE
    // ==========================

    const themeToggle = document.getElementById("themeToggle");
    const root = document.documentElement;

    const savedTheme = localStorage.getItem("theme") || "light";

    root.setAttribute("data-theme", savedTheme);

    updateThemeIcon(savedTheme);

    if (themeToggle) {

        themeToggle.addEventListener("click", function () {

            const currentTheme = root.getAttribute("data-theme");

            const newTheme =
                currentTheme === "dark"
                    ? "light"
                    : "dark";

            root.setAttribute("data-theme", newTheme);

            localStorage.setItem("theme", newTheme);

            updateThemeIcon(newTheme);

        });

    }

    function updateThemeIcon(theme) {

        if (!themeToggle) return;

        themeToggle.innerHTML =
            theme === "dark"
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';

   }