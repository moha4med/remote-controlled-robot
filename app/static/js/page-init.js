$(function () {
  // Initialize page plugins
  var $dashboard = $("[data-dashboard-board]");
  var $control = $("[data-control-surface]");
  var $sensors = $("[data-sensors-dashboard]");

  if ($dashboard.length) {
    $dashboard.robotDashboardBoard();
  }
  if ($control.length) {
    $control.robotControlSurface();
  }
  if ($sensors.length) {
    $sensors.robotSensorsDashboard();
  }

  // Theme toggle
  var $themeToggles = $("[data-theme-toggle]");

  function setTheme(mode) {
    var isLight = mode === "light";
    document.documentElement.classList.toggle("theme-light", isLight);
    $themeToggles.attr("aria-pressed", isLight ? "true" : "false");
    $themeToggles.attr("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
    window.localStorage.setItem("theme", isLight ? "light" : "dark");
  }

  (function initTheme() {
    var saved = window.localStorage.getItem("theme");
    if (saved) {
      setTheme(saved);
      return;
    }
    var prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    setTheme(prefersLight ? "light" : "dark");
  })();

  if ($themeToggles.length) {
    $themeToggles.on("click", function () {
      var isLight = document.documentElement.classList.contains("theme-light");
      setTheme(isLight ? "dark" : "light");
    });
  }
});