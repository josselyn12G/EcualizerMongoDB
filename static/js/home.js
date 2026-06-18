/* ═══════════════════════════════════════════
   ECUALIZER — home.js
   Scroll reveal + navbar sticky
   ═══════════════════════════════════════════ */

(function () {
  "use strict";

  /* ── 1. NAVBAR: se vuelve opaco al hacer scroll ── */
  const navbar = document.getElementById("navbar");

  function handleNavbar() {
    if (!navbar) return;
    if (window.scrollY > 60) {
      navbar.classList.add("scrolled");
    } else {
      navbar.classList.remove("scrolled");
    }
  }

  window.addEventListener("scroll", handleNavbar, { passive: true });
  handleNavbar(); // Estado inicial

  /* ── 2. REVEAL: elementos entran al hacer scroll ── */
  const revealEls = document.querySelectorAll(".reveal-up");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            // No dejar de observar para que el efecto se repita si el usuario sube
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    revealEls.forEach((el) => observer.observe(el));
  } else {
    // Fallback sin IntersectionObserver
    revealEls.forEach((el) => el.classList.add("visible"));
  }

  /* ── 3. HERO: disparar animaciones de entrada inmediatamente ── */
  // Los elementos del hero son visibles desde el inicio, se revelan con delay
  document.addEventListener("DOMContentLoaded", function () {
    // Pequeño tick para que el navegador procese los estilos antes de disparar
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.querySelectorAll(".hero .reveal-up").forEach((el) => {
          el.classList.add("visible");
        });
      });
    });
  });

  // Fallback si DOMContentLoaded ya pasó
  if (document.readyState !== "loading") {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.querySelectorAll(".hero .reveal-up").forEach((el) => {
          el.classList.add("visible");
        });
      });
    });
  }

  /* ── 4. PARALLAX suave en la imagen de fondo del hero ── */
  const heroBgImg = document.querySelector(".hero-bg-img");

  function handleParallax() {
    if (!heroBgImg) return;
    const scrollY = window.scrollY;
    // Mueve la imagen 30% más lento que el scroll
    heroBgImg.style.transform = `translateY(${scrollY * 0.3}px)`;
  }

  window.addEventListener("scroll", handleParallax, { passive: true });

})();