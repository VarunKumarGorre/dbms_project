/**
 * RPGMS Form Utilities & Validation
 * File: app/static/js/forms.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Money Input Formatting (Indian System on blur, plain float on submit)
  function formatIndianGrouping(numStr) {
    if (!numStr) return "";
    const clean = numStr.toString().replace(/[^0-9.]/g, "");
    if (!clean) return "";
    const parts = clean.split(".");
    let intPart = parts[0];
    const decPart = parts.length > 1 ? "." + parts[1].substring(0, 2) : "";

    if (intPart.length <= 3) {
      return intPart + decPart;
    }
    const last3 = intPart.slice(-3);
    const rest = intPart.slice(0, -3);
    const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
    return grouped + "," + last3 + decPart;
  }

  document.querySelectorAll(".input-money").forEach(input => {
    // On focus: clean commas for editing
    input.addEventListener("focus", () => {
      input.value = input.value.replace(/,/g, "");
    });

    // On blur: format with commas
    input.addEventListener("blur", () => {
      input.value = formatIndianGrouping(input.value);
    });

    // Initial format if populated
    if (input.value) {
      input.value = formatIndianGrouping(input.value);
    }
  });

  // 2. Textarea Character Counters
  document.querySelectorAll("textarea[maxlength]").forEach(textarea => {
    const max = textarea.getAttribute("maxlength");
    const counterId = textarea.getAttribute("data-counter");
    const counterEl = counterId ? document.getElementById(counterId) : null;

    function updateCount() {
      if (counterEl) {
        counterEl.textContent = `${textarea.value.length}/${max}`;
      }
    }

    textarea.addEventListener("input", updateCount);
    updateCount();
  });

  // 3. Form Submission Handling (Clean money inputs, button spinner)
  document.querySelectorAll("form").forEach(form => {
    let isSubmitting = false;

    form.addEventListener("submit", (e) => {
      if (isSubmitting) {
        e.preventDefault();
        return;
      }

      // Strip commas from money fields before sending to server
      form.querySelectorAll(".input-money").forEach(input => {
        input.value = input.value.replace(/,/g, "");
      });

      // Show spinner on submit button
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        isSubmitting = true;
        submitBtn.disabled = true;
        const origText = submitBtn.innerHTML;
        submitBtn.innerHTML = `
          <svg class="icon spin" style="animation: spin 1s linear infinite;" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke-width="4" stroke-dasharray="31.4" stroke-dashoffset="10"/>
          </svg> Saving...
        `;
      }
    });
  });

  // 4. Dirty Form Leave Confirmation
  let isFormDirty = false;
  document.querySelectorAll("form.warn-unsaved input, form.warn-unsaved textarea, form.warn-unsaved select").forEach(el => {
    el.addEventListener("change", () => { isFormDirty = true; });
  });

  window.addEventListener("beforeunload", (e) => {
    if (isFormDirty) {
      e.preventDefault();
      e.returnValue = "You have unsaved changes. Are you sure you want to leave?";
    }
  });

  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", () => { isFormDirty = false; });
  });
});
