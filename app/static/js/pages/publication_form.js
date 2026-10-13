/**
 * RPGMS Publication Form Logic (Authors repeater & DOI validation)
 * File: app/static/js/pages/publication_form.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  const authorsContainer = document.getElementById("authors-list");
  const addAuthorBtn = document.getElementById("btn-add-author");
  const doiInput = document.getElementById("pub-doi-input");
  const doiWarning = document.getElementById("pub-doi-warning");

  // 1. Author Repeater Management
  function renumberAuthors() {
    const rows = authorsContainer.querySelectorAll(".author-row");
    rows.forEach((row, idx) => {
      const orderSpan = row.querySelector(".author-order-label");
      if (orderSpan) orderSpan.textContent = idx + 1;
    });
  }

  if (addAuthorBtn && authorsContainer) {
    addAuthorBtn.addEventListener("click", () => {
      const rowCount = authorsContainer.querySelectorAll(".author-row").length + 1;
      const row = document.createElement("div");
      row.className = "author-row";
      row.style.cssText = "display: flex; align-items: center; gap: var(--s3); margin-bottom: var(--s2); padding: var(--s2); background: var(--surface-2); border-radius: var(--radius-sm);";

      row.innerHTML = `
        <span class="author-order-label" style="font-weight: 700; width: 24px;">${rowCount}</span>
        <div style="flex: 1;">
          <input type="text" class="input researcher-typeahead-input" placeholder="Search researcher by name..." required>
          <input type="hidden" name="author_ids[]" class="author-id-hidden">
        </div>
        <label style="display: flex; align-items: center; gap: 4px; font-size: 12px; cursor: pointer;">
          <input type="checkbox" name="is_corresponding[]" value="${rowCount}"> Corr.
        </label>
        <button type="button" class="btn btn-ghost btn-sm btn-remove-author" title="Remove author">
          <svg class="icon"><use href="/static/img/icons.svg#trash"/></svg>
        </button>
      `;

      authorsContainer.appendChild(row);
      bindAuthorRowEvents(row);
      renumberAuthors();
    });
  }

  function bindAuthorRowEvents(row) {
    const removeBtn = row.querySelector(".btn-remove-author");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        row.remove();
        renumberAuthors();
      });
    }

    const typeaheadInput = row.querySelector(".researcher-typeahead-input");
    const hiddenId = row.querySelector(".author-id-hidden");
    if (typeaheadInput && hiddenId) {
      new Typeahead(typeaheadInput, {
        endpoint: (q) => `/api/researchers/search?q=${encodeURIComponent(q)}`,
        targetIdInput: hiddenId
      });
    }
  }

  document.querySelectorAll(".author-row").forEach(bindAuthorRowEvents);

  // 2. DOI Existence Live Check
  if (doiInput && doiWarning) {
    let doiTimer = null;
    doiInput.addEventListener("input", () => {
      clearTimeout(doiTimer);
      const doi = doiInput.value.trim();
      if (!doi) {
        doiWarning.style.display = "none";
        return;
      }
      doiTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/doi-exists?doi=${encodeURIComponent(doi)}`);
          if (!res.ok) return;
          const data = await res.json();
          if (data.exists) {
            doiWarning.style.display = "block";
            doiWarning.textContent = "(!) A publication with this DOI already exists (BR-08)";
          } else {
            doiWarning.style.display = "none";
          }
        } catch (e) {
          console.error(e);
        }
      }, 300);
    });
  }
});
