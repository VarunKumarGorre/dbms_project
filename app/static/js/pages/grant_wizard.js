/**
 * RPGMS Grant 3-Step Wizard Logic
 * File: app/static/js/pages/grant_wizard.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  const step1 = document.getElementById("wizard-step-1");
  const step2 = document.getElementById("wizard-step-2");
  const step3 = document.getElementById("wizard-step-3");

  const toStep2Btn = document.getElementById("btn-to-step-2");
  const backToStep1Btn = document.getElementById("btn-back-to-step-1");
  const toStep3Btn = document.getElementById("btn-to-step-3");
  const backToStep2Btn = document.getElementById("btn-back-to-step-2");

  const amountInput = document.getElementById("grant-amount-input");
  const allocInputs = document.querySelectorAll(".alloc-head-input");
  const allocSumDisplay = document.getElementById("alloc-sum-display");
  const unallocDisplay = document.getElementById("unalloc-display");
  const allocProgressBar = document.getElementById("alloc-progress-bar");
  const allocWarning = document.getElementById("alloc-warning");
  const distributeEvenlyBtn = document.getElementById("btn-distribute-evenly");

  function getGrantAmount() {
    return parseFloat((amountInput.value || "0").replace(/,/g, "")) || 0;
  }

  function updateAllocations() {
    const totalAmount = getGrantAmount();
    let sum = 0;
    allocInputs.forEach(input => {
      const val = parseFloat((input.value || "0").replace(/,/g, "")) || 0;
      sum += val;
    });

    const unallocated = totalAmount - sum;
    if (allocSumDisplay) allocSumDisplay.textContent = `₹ ${sum.toLocaleString("en-IN")}`;
    if (unallocDisplay) unallocDisplay.textContent = `₹ ${unallocated.toLocaleString("en-IN")}`;

    const pct = totalAmount > 0 ? (sum / totalAmount) * 100 : 0;
    if (allocProgressBar) {
      allocProgressBar.style.width = `${Math.min(100, pct)}%`;
      if (pct > 100) {
        allocProgressBar.style.background = "var(--danger)";
        if (allocWarning) {
          allocWarning.style.display = "block";
          allocWarning.textContent = `Allocations exceed grant total by ₹ ${(sum - totalAmount).toLocaleString("en-IN")} (BR-09)`;
        }
        if (toStep3Btn) toStep3Btn.disabled = true;
      } else {
        allocProgressBar.style.background = "var(--primary)";
        if (allocWarning) allocWarning.style.display = "none";
        if (toStep3Btn) toStep3Btn.disabled = false;
      }
    }
  }

  allocInputs.forEach(inp => inp.addEventListener("input", updateAllocations));
  if (amountInput) amountInput.addEventListener("input", updateAllocations);

  if (distributeEvenlyBtn) {
    distributeEvenlyBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const totalAmount = getGrantAmount();
      if (totalAmount <= 0) return;
      const count = allocInputs.length;
      if (count === 0) return;
      const share = Math.floor(totalAmount / count);
      allocInputs.forEach((inp, idx) => {
        inp.value = (idx === 0 ? share + (totalAmount - share * count) : share).toString();
      });
      updateAllocations();
    });
  }

  // Stepper navigation
  if (toStep2Btn) {
    toStep2Btn.addEventListener("click", () => {
      step1.style.display = "none";
      step2.style.display = "block";
      updateAllocations();
    });
  }
  if (backToStep1Btn) {
    backToStep1Btn.addEventListener("click", () => {
      step2.style.display = "none";
      step1.style.display = "block";
    });
  }
  if (toStep3Btn) {
    toStep3Btn.addEventListener("click", () => {
      step2.style.display = "none";
      step3.style.display = "block";

      // Populate review summary
      const reviewGrantNo = document.getElementById("review-grant-no");
      const reviewAmount = document.getElementById("review-amount");
      if (reviewGrantNo) reviewGrantNo.textContent = document.getElementById("grant-number-input").value;
      if (reviewAmount) reviewAmount.textContent = `₹ ${getGrantAmount().toLocaleString("en-IN")}`;
    });
  }
  if (backToStep2Btn) {
    backToStep2Btn.addEventListener("click", () => {
      step3.style.display = "none";
      step2.style.display = "block";
    });
  }
});
