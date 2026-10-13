/**
 * RPGMS Accessible Typeahead Component
 * File: app/static/js/typeahead.js
 * Author: Antigravity AI
 */

class Typeahead {
  constructor(inputElement, options = {}) {
    this.input = inputElement;
    this.endpoint = options.endpoint; // function(query) returning URL
    this.targetIdInput = options.targetIdInput; // hidden input to store ID
    this.onSelect = options.onSelect || (() => {});
    this.minChars = options.minChars || 2;
    this.debounceMs = options.debounceMs || 250;

    this.timer = null;
    this.items = [];
    this.activeIndex = -1;

    this.initDropdown();
    this.bindEvents();
  }

  initDropdown() {
    this.dropdown = document.createElement("div");
    this.dropdown.className = "typeahead-dropdown";
    this.dropdown.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      box-shadow: var(--shadow);
      max-height: 240px;
      overflow-y: auto;
      z-index: 1050;
      display: none;
    `;
    this.input.parentElement.style.position = "relative";
    this.input.parentElement.appendChild(this.dropdown);
  }

  bindEvents() {
    this.input.addEventListener("input", () => {
      clearTimeout(this.timer);
      const query = this.input.value.trim();
      if (query.length < this.minChars) {
        this.hide();
        return;
      }
      this.timer = setTimeout(() => this.fetchResults(query), this.debounceMs);
    });

    this.input.addEventListener("keydown", (e) => {
      if (!this.isOpen()) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        this.activeIndex = Math.min(this.activeIndex + 1, this.items.length - 1);
        this.highlightActive();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.activeIndex = Math.max(this.activeIndex - 1, 0);
        this.highlightActive();
      } else if (e.key === "Enter") {
        if (this.activeIndex >= 0 && this.activeIndex < this.items.length) {
          e.preventDefault();
          this.selectItem(this.items[this.activeIndex]);
        }
      } else if (e.key === "Escape") {
        this.hide();
      }
    });

    document.addEventListener("click", (e) => {
      if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
        this.hide();
      }
    });
  }

  async fetchResults(query) {
    try {
      const url = this.endpoint(query);
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      this.items = data || [];
      this.activeIndex = -1;
      this.render();
    } catch (err) {
      console.error("Typeahead error:", err);
    }
  }

  render() {
    if (this.items.length === 0) {
      this.dropdown.innerHTML = `<div style="padding: 10px 12px; font-size: 13px; color: var(--text-muted);">No matching results</div>`;
      this.show();
      return;
    }

    this.dropdown.innerHTML = "";
    this.items.forEach((item, index) => {
      const itemEl = document.createElement("div");
      itemEl.className = "typeahead-item";
      itemEl.style.cssText = `
        padding: 8px 12px;
        cursor: pointer;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      `;

      const title = item.name || item.title || item.grant_number || item.code || "";
      const subtitle = item.dept || item.designation || item.project_code || item.agency || "";

      itemEl.innerHTML = `
        <span style="font-weight: 500;">${title}</span>
        <span style="font-size: 11px; color: var(--text-muted);">${subtitle}</span>
      `;

      itemEl.addEventListener("mouseenter", () => {
        this.activeIndex = index;
        this.highlightActive();
      });

      itemEl.addEventListener("click", () => {
        this.selectItem(item);
      });

      this.dropdown.appendChild(itemEl);
    });

    this.show();
  }

  highlightActive() {
    const children = this.dropdown.querySelectorAll(".typeahead-item");
    children.forEach((child, index) => {
      if (index === this.activeIndex) {
        child.style.background = "var(--primary-soft)";
        child.style.color = "var(--primary)";
      } else {
        child.style.background = "var(--surface)";
        child.style.color = "var(--text)";
      }
    });
  }

  selectItem(item) {
    const title = item.name || item.title || item.grant_number || item.code || "";
    this.input.value = title;
    if (this.targetIdInput) {
      this.targetIdInput.value = item.id;
    }
    this.hide();
    this.onSelect(item);
  }

  show() {
    this.dropdown.style.display = "block";
  }

  hide() {
    this.dropdown.style.display = "none";
    this.activeIndex = -1;
  }

  isOpen() {
    return this.dropdown.style.display === "block";
  }
}

window.Typeahead = Typeahead;
