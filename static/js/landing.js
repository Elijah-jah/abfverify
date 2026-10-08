document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    /* ==========================
       THEME TOGGLE
       Convention: dark is default, body.light = light,
       preference stored in localStorage under "theme".
    ========================== */

    var themeToggle = document.getElementById("themeToggle");

    function applyTheme(isLight) {
        document.body.classList.toggle("light", isLight);
        if (themeToggle) {
            themeToggle.innerHTML = isLight
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';
        }
    }

    /* initial state (pre-paint script in <head> already set body.light) */
    applyTheme(document.body.classList.contains("light"));

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            var isLight = !document.body.classList.contains("light");
            applyTheme(isLight);
            try {
                localStorage.setItem("theme", isLight ? "light" : "dark");
            } catch (e) {}
        });
    }

    /* ==========================
       BACK TO TOP
    ========================== */

    var backTop = document.getElementById("backToTop");

    if (backTop) {
        window.addEventListener("scroll", function () {
            backTop.classList.toggle("show", window.scrollY > 400);
        });

        backTop.addEventListener("click", function () {
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    /* ==========================
       SCROLL REVEAL
    ========================== */

    var animated = document.querySelectorAll(".rv");

    if ("IntersectionObserver" in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("animate");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });

        animated.forEach(function (el) { observer.observe(el); });
    } else {
        animated.forEach(function (el) { el.classList.add("animate"); });
    }

    /* ==========================
       ACTIVE NAV LINK
    ========================== */

    var sections = document.querySelectorAll("section[id]");
    var navLinks = document.querySelectorAll(".nav-link");

    window.addEventListener("scroll", function () {
        var current = "";

        sections.forEach(function (section) {
            if (window.scrollY >= section.offsetTop - 140) {
                current = section.getAttribute("id");
            }
        });

        navLinks.forEach(function (link) {
            link.classList.remove("active");
            if (link.getAttribute("href") === "#" + current) {
                link.classList.add("active");
            }
        });
    });

    /* ==========================
       PHONE TILT (desktop only)
    ========================== */

    var phone = document.querySelector(".phone-frame");
    var finePointer = window.matchMedia && window.matchMedia("(pointer: fine)").matches;

    if (phone && finePointer) {
        window.addEventListener("mousemove", function (e) {
            var x = (window.innerWidth / 2 - e.clientX) / 80;
            var y = (window.innerHeight / 2 - e.clientY) / 80;
            phone.style.transform =
                "rotateY(" + x + "deg) rotateX(" + (-y) + "deg)";
        });

        document.addEventListener("mouseleave", function () {
            phone.style.transform = "rotateY(0deg) rotateX(0deg)";
        });
    }

});