// ─── InventoryPro Client-Side JS (Modern) ───

document.addEventListener("DOMContentLoaded", () => {

    // ── Dark-mode toggle ──
    const toggle = document.getElementById("themeToggle");
    const html = document.documentElement;
    const saved = localStorage.getItem("theme") || "light";
    html.setAttribute("data-bs-theme", saved);
    updateIcon(saved);

    if (toggle) {
        toggle.addEventListener("click", () => {
            const next = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            html.setAttribute("data-bs-theme", next);
            localStorage.setItem("theme", next);
            updateIcon(next);
        });
    }

    function updateIcon(theme) {
        if (!toggle) return;
        toggle.innerHTML = theme === "dark"
            ? '<i class="bi bi-sun-fill"></i>'
            : '<i class="bi bi-moon-fill"></i>';
    }

    // ── Delete confirmation ──
    document.querySelectorAll(".delete-form").forEach(form => {
        form.addEventListener("submit", e => {
            if (!confirm("Are you sure you want to delete this item? This cannot be undone.")) {
                e.preventDefault();
            }
        });
    });

    // ── Live search debounce ──
    const searchInput = document.getElementById("searchInput");
    const searchCol = document.getElementById("searchCol");
    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => liveSearch(), 500);
        });
    }
    if (searchCol) {
        searchCol.addEventListener("change", () => liveSearch());
    }

    function liveSearch() {
        const q = searchInput?.value || "";
        const col = searchCol?.value || "";
        document.getElementById("searchForm")?.submit();
    }

    // ── Bootstrap form validation ──
    document.querySelectorAll(".needs-validation").forEach(form => {
        form.addEventListener("submit", e => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });

    // ── Auto-dismiss alerts after 5 seconds ──
    document.querySelectorAll(".alert-dismissible").forEach(alert => {
        setTimeout(() => {
            const btn = alert.querySelector(".btn-close");
            if (btn) btn.click();
        }, 5000);
    });

    // ── Add active class to current nav link ──
    const currentPath = window.location.pathname;
    document.querySelectorAll(".navbar .nav-link").forEach(link => {
        const href = link.getAttribute("href");
        if (href && currentPath === href) {
            link.classList.add("active");
        } else if (href && currentPath.startsWith(href) && href !== "/") {
            link.classList.add("active");
        }
    });


});

// ── Image modal helper ── function showImage(src, title) { document.getElementById("imgModalSrc").src = src; document.getElementById("imgModalLabel").textContent = title; }