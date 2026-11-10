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
            if (!confirm("Delete this item? This cannot be undone.")) {
                e.preventDefault();
            }
        });
    });

    // ── Live search (debounced form submit, keeps caret at end after reload) ──
    const searchInput = document.getElementById("searchInput");
    const searchCol = document.getElementById("searchCol");
    const searchForm = document.getElementById("searchForm");
    let debounceTimer;

    if (searchInput && searchForm) {
        if (searchInput.value) {
            searchInput.focus();
            searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length);
        }
        searchInput.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => searchForm.submit(), 600);
        });
        searchCol?.addEventListener("change", () => searchForm.submit());
    }

    // ── Image preview modal (data-attribute driven, no inline JS) ──
    document.querySelectorAll("[data-preview-src]").forEach(img => {
        img.addEventListener("click", () => {
            document.getElementById("imgModalSrc").src = img.dataset.previewSrc;
            document.getElementById("imgModalLabel").textContent = img.dataset.previewTitle || "Image";
        });
    });

    // ── Confirm dialogs for any form with data-confirm ──
    document.querySelectorAll("form[data-confirm]").forEach(form => {
        form.addEventListener("submit", e => {
            if (!confirm(form.dataset.confirm)) e.preventDefault();
        });
    });

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
    document.querySelectorAll(".toast-stack .alert").forEach(alert => {
        setTimeout(() => {
            const btn = alert.querySelector(".btn-close");
            if (btn) btn.click();
        }, 5000);
    });


});
