/**
 * RPGMS Expenditure Live Balance Calculator
 * File: app/static/js/pages/expenditure.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  const grantSelect = document.getElementById("exp-grant-select");
  const headSelect = document.getElementById("exp-head-select");
  const amountInput = document.getElementById("exp-amount-input");
  const dateInput = document.getElementById("exp-date-input");
  const submitBtn = document.getElementById("exp-submit-btn");

  const liveGrantCode = document.getElementById("live-grant-code");
  const liveGrantTotal = document.getElementById("live-grant-total");
  const liveGrantSpent = document.getElementById("live-grant-spent");
  const liveHeadAllocated = document.getElementById("live-head-allocated");
  const liveHeadSpent = document.getElementById("live-head-spent");
  const liveHeadRemaining = document.getElementById("live-head-remaining");
  const liveAfterEntry = document.getElementById("live-after-entry");
  const liveWarning = document.getElementById("live-budget-warning");

  let currentGrantData = null;

  async function loadGrantHeads(grantId) {
    if (!grantId) return;
    try {
      const res = await fetch(`/api/grants/${grantId}/heads`);
      if (!res.ok) return;
      currentGrantData = await res.json();

      // Populate head options
      headSelect.innerHTML = '<option value="">-- Select Budget Head --</option>';
      currentGrantData.heads.forEach(h => {
        const opt = document.createElement("option");
        opt.value = h.head_id;
        opt.textContent = `${h.head_name} (Rem: ₹ ${h.remaining.toLocaleString("en-IN")})`;
        opt.dataset.allocated = h.allocated;
        opt.dataset.spent = h.spent;
        opt.dataset.remaining = h.remaining;
        headSelect.appendChild(opt);
      });

      // Update date limits (BR-07)
      if (dateInput) {
        dateInput.min = currentGrantData.grant_start;
        dateInput.max = currentGrantData.grant_end;
      }

      // Update grant total tiles
      if (liveGrantCode) liveGrantCode.textContent = `${currentGrantData.grant_number} (${currentGrantData.project_code})`;
      if (liveGrantTotal) liveGrantTotal.textContent = `₹ ${currentGrantData.totals.amount.toLocaleString("en-IN")}`;
      if (liveGrantSpent) liveGrantSpent.textContent = `₹ ${currentGrantData.totals.spent.toLocaleString("en-IN")} (${currentGrantData.totals.used_pct}%)`;

      updateBalancePreview();
    } catch (e) {
      console.error("Error loading grant heads:", e);
    }
  }

  function updateBalancePreview() {
    const selectedHead = headSelect.options[headSelect.selectedIndex];
    if (!selectedHead || !selectedHead.value) {
      if (liveHeadAllocated) liveHeadAllocated.textContent = "—";
      if (liveHeadSpent) liveHeadSpent.textContent = "—";
      if (liveHeadRemaining) liveHeadRemaining.textContent = "—";
      if (liveAfterEntry) liveAfterEntry.textContent = "—";
      if (liveWarning) liveWarning.style.display = "none";
      return;
    }

    const alloc = parseFloat(selectedHead.dataset.allocated) || 0;
    const spent = parseFloat(selectedHead.dataset.spent) || 0;
    const rem = parseFloat(selectedHead.dataset.remaining) || 0;
    const enterAmt = parseFloat((amountInput.value || "0").replace(/,/g, "")) || 0;

    const afterRem = rem - enterAmt;

    if (liveHeadAllocated) liveHeadAllocated.textContent = `₹ ${alloc.toLocaleString("en-IN")}`;
    if (liveHeadSpent) liveHeadSpent.textContent = `₹ ${spent.toLocaleString("en-IN")}`;
    if (liveHeadRemaining) liveHeadRemaining.textContent = `₹ ${rem.toLocaleString("en-IN")}`;

    if (liveAfterEntry) {
      liveAfterEntry.textContent = `₹ ${afterRem.toLocaleString("en-IN")}`;
      liveAfterEntry.style.color = afterRem < 0 ? "var(--danger)" : "var(--success)";
    }

    if (enterAmt > rem) {
      if (liveWarning) {
        liveWarning.style.display = "block";
        liveWarning.textContent = `(!) Exceeds allocation by ₹ ${(enterAmt - rem).toLocaleString("en-IN")} (BR-06)`;
      }
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.title = "Amount exceeds remaining head balance";
      }
    } else {
      if (liveWarning) liveWarning.style.display = "none";
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.title = "";
      }
    }
  }

  if (grantSelect) {
    grantSelect.addEventListener("change", () => loadGrantHeads(grantSelect.value));
    if (grantSelect.value) {
      loadGrantHeads(grantSelect.value);
    }
  }

  if (headSelect) headSelect.addEventListener("change", updateBalancePreview);
  if (amountInput) amountInput.addEventListener("input", updateBalancePreview);
});
