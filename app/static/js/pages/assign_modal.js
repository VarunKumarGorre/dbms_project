/**
 * RPGMS Assign Investigator Modal Logic
 * File: app/static/js/pages/assign_modal.js
 * Author: Antigravity AI
 */

document.addEventListener("DOMContentLoaded", () => {
  const researcherSelect = document.getElementById("assign-researcher-select");
  const effortInput = document.getElementById("assign-effort-input");
  const effortSlider = document.getElementById("assign-effort-slider");
  const workloadPreview = document.getElementById("assign-workload-preview");
  const workloadWarning = document.getElementById("assign-workload-warning");
  const submitBtn = document.getElementById("assign-submit-btn");

  let currentWorkload = 0;

  async function checkWorkload(researcherId) {
    if (!researcherId) {
      currentWorkload = 0;
      updatePreview();
      return;
    }
    try {
      const res = await fetch(`/api/researchers/${researcherId}/workload`);
      if (!res.ok) return;
      const data = await res.json();
      currentWorkload = data.current_percent || 0;
      updatePreview();
    } catch (e) {
      console.error("Error fetching researcher workload:", e);
    }
  }

  function updatePreview() {
    const adding = parseFloat(effortInput.value) || 0;
    const total = currentWorkload + adding;

    if (workloadPreview) {
      workloadPreview.textContent = `${currentWorkload}%  ====>  ${total}%`;
    }

    if (total > 100) {
      if (workloadWarning) {
        workloadWarning.style.display = "block";
        workloadWarning.textContent = `(!) Total effort ${total}% exceeds 100% across active projects (BR-11)`;
      }
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.title = "Combined effort exceeds 100%";
      }
    } else {
      if (workloadWarning) workloadWarning.style.display = "none";
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.title = "";
      }
    }
  }

  if (effortSlider && effortInput) {
    effortSlider.addEventListener("input", () => {
      effortInput.value = effortSlider.value;
      updatePreview();
    });
    effortInput.addEventListener("input", () => {
      effortSlider.value = effortInput.value;
      updatePreview();
    });
  }

  if (researcherSelect) {
    researcherSelect.addEventListener("change", () => {
      checkWorkload(researcherSelect.value);
    });
  }
});
