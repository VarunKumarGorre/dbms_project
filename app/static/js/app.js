/**
 * RPGMS Core Client Application Logic
 * File: app/static/js/app.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Theme Management (Light / Dark)
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const storedTheme = (() => {
    try { return localStorage.getItem("rpgms-theme"); } catch (e) { return null; }
  })();

  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = storedTheme || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", initialTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("rpgms-theme", next); } catch (e) {}
      window.dispatchEvent(new CustomEvent("theme-changed", { detail: next }));
    });
  }

  // 2. Sidebar Collapse (Desktop)
  const collapseBtn = document.getElementById("sidebar-collapse-btn");
  const isCollapsed = (() => {
    try { return localStorage.getItem("rpgms-sidebar-collapsed") === "true"; } catch (e) { return false; }
  })();
  if (isCollapsed) {
    document.body.classList.add("sidebar-collapsed");
  }

  if (collapseBtn) {
    collapseBtn.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-collapsed");
      const state = document.body.classList.contains("sidebar-collapsed");
      try { localStorage.setItem("rpgms-sidebar-collapsed", state); } catch (e) {}
    });
  }

  // 3. Mobile Sidebar Drawer Toggle
  const mobileMenuBtn = document.getElementById("mobile-menu-btn");
  const sidebar = document.querySelector(".sidebar");
  if (mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      sidebar.classList.toggle("mobile-open");
    });
    document.addEventListener("click", (e) => {
      if (!sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
        sidebar.classList.remove("mobile-open");
      }
    });
  }

  // 4. Global Search Keyboard Shortcut ('/')
  const globalSearchInput = document.getElementById("global-search-input");
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== globalSearchInput && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      e.preventDefault();
      if (globalSearchInput) {
        globalSearchInput.focus();
      }
    }
  });

  // Global search autocomplete
  if (globalSearchInput) {
    const searchDropdown = document.getElementById("global-search-dropdown");
    let searchTimer = null;

    globalSearchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const query = globalSearchInput.value.trim();
      if (query.length < 2) {
        if (searchDropdown) searchDropdown.style.display = "none";
        return;
      }
      searchTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
          if (!res.ok) return;
          const data = await res.json();
          renderGlobalSearchResults(data, searchDropdown);
        } catch (err) {
          console.error("Global search error:", err);
        }
      }, 250);
    });

    document.addEventListener("click", (e) => {
      if (searchDropdown && !globalSearchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.style.display = "none";
      }
    });
  }

  function renderGlobalSearchResults(data, dropdown) {
    if (!dropdown) return;
    let html = "";
    let hasResults = false;

    for (const [group, items] of Object.entries(data)) {
      if (items && items.length > 0) {
        hasResults = true;
        html += `<div style="padding: 6px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; background: var(--surface-2); color: var(--text-muted);">${group}</div>`;
        items.forEach(it => {
          let link = "#";
          let label = it.title || it.name || it.code || it.grant_number;
          let sub = it.code || it.dept || it.agency || it.status || "";
          if (group === "projects") link = `/projects/${it.id}`;
          else if (group === "researchers") link = `/investigators/${it.id}`;
          else if (group === "grants") link = `/grants/${it.id}`;
          else if (group === "publications") link = `/publications/${it.id}`;
          else if (group === "patents") link = `/patents/${it.id}`;

          html += `
            <a href="${link}" style="display: flex; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text);">
              <span>${label}</span>
              <span style="font-size: 11px; color: var(--text-muted);">${sub}</span>
            </a>
          `;
        });
      }
    }

    if (!hasResults) {
      html = `<div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 13px;">No matching records found.</div>`;
    }

    dropdown.innerHTML = html;
    dropdown.style.display = "block";
  }

  // 5. User Profile Menu Toggle
  const userProfileBtn = document.getElementById("user-profile-btn");
  const userDropdown = document.getElementById("user-dropdown");
  if (userProfileBtn && userDropdown) {
    userProfileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle("open");
    });
    document.addEventListener("click", (e) => {
      if (!userDropdown.contains(e.target) && !userProfileBtn.contains(e.target)) {
        userDropdown.classList.remove("open");
      }
    });
  }

  // 6. Toasts Auto-Dismiss
  document.querySelectorAll(".toast").forEach(toast => {
    setTimeout(() => {
      toast.style.transition = "opacity 300ms ease, transform 300ms ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }, 5000);

    const closeBtn = toast.querySelector(".toast-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => toast.remove());
    }
  });

  // 7. Modals helper
  document.querySelectorAll("[data-modal-open]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute("data-modal-open");
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add("open");
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const modal = btn.closest(".modal-backdrop");
      if (modal) modal.classList.remove("open");
    });
  });

  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove("open");
      }
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.open").forEach(m => m.classList.remove("open"));
    }
  });

  // 8. Notifications Bell Badge Auto-fetch
  const bellBadge = document.getElementById("bell-count-badge");
  if (bellBadge) {
    fetch("/api/notifications/count")
      .then(res => res.json())
      .then(data => {
        if (data && data.overdue > 0) {
          bellBadge.textContent = data.overdue;
          bellBadge.style.display = "flex";
        } else {
          bellBadge.style.display = "none";
        }
      })
      .catch(() => {});
  }
});
