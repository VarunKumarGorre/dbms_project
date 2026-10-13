/**
 * RPGMS Chart.js Rendering Engine
 * File: app/static/js/charts.js
 * Author: Antigravity AI
 */

window.RPGMSCharts = (() => {
  function getThemeColors() {
    const rootStyle = getComputedStyle(document.documentElement);
    return {
      primary: rootStyle.getPropertyValue("--chart-primary").trim() || "#2457D6",
      secondary: rootStyle.getPropertyValue("--chart-secondary").trim() || "#A9BDF2",
      success: rootStyle.getPropertyValue("--chart-success").trim() || "#1E9E6A",
      warning: rootStyle.getPropertyValue("--chart-warning").trim() || "#C98100",
      danger: rootStyle.getPropertyValue("--chart-danger").trim() || "#D64545",
      info: rootStyle.getPropertyValue("--chart-info").trim() || "#2B8CD6",
      border: rootStyle.getPropertyValue("--border").trim() || "#E3E6EF",
      text: rootStyle.getPropertyValue("--text").trim() || "#1B2133",
      textMuted: rootStyle.getPropertyValue("--text-muted").trim() || "#6B7390",
    };
  }

  const registeredCharts = [];

  function registerChart(canvasId, createFn) {
    if (typeof Chart === "undefined") {
      const canvas = document.getElementById(canvasId);
      if (canvas && canvas.parentElement) {
        const fallback = document.createElement("div");
        fallback.style.cssText = "padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;";
        fallback.textContent = "Chart visualization unavailable (Chart library not loaded). Please view table data.";
        canvas.parentElement.appendChild(fallback);
      }
      return;
    }

    let instance = createFn(getThemeColors());
    if (instance) {
      registeredCharts.push({ canvasId, createFn, instance });
    }
  }

  // Handle theme changes dynamically
  window.addEventListener("theme-changed", () => {
    const colors = getThemeColors();
    registeredCharts.forEach(item => {
      if (item.instance) {
        item.instance.destroy();
        item.instance = item.createFn(colors);
      }
    });
  });

  return {
    getThemeColors,
    register: registerChart
  };
})();
