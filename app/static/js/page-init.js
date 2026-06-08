$(function () {
  // Initialize page plugins
  var $dashboard = $("[data-dashboard-board]");
  var $control = $("[data-control-surface]");
  var $sensors = $("[data-sensors-dashboard]");
  var $captures = $("[data-captures-page]");

  if ($dashboard.length) {
    $dashboard.robotDashboardBoard();
  }
  if ($control.length) {
    $control.robotControlSurface();
  }
  if ($sensors.length) {
    $sensors.robotSensorsDashboard();
  }
  if ($captures.length) {
    $captures.capturesGallery();
  }

  // Chart view toggle (Real-time / Hourly) — sensors page
  var $viewToggle = $("#chartViewToggle");
  var $hourlyRange = $("#hourlyRange");
  var $rangeButtons = $hourlyRange.find("button");

  if ($viewToggle.length) {
    $viewToggle.on("click", "button", function () {
      var $btn = $(this);
      var view = $btn.data("view");
      $viewToggle.find("button").removeClass("active");
      $btn.addClass("active");
      if (view === "hourly") {
        $hourlyRange.show();
      } else {
        $hourlyRange.hide();
      }
      if ($sensors.length) {
        $sensors.robotSensorsDashboard("switchView", view);
        $sensors.robotSensorsDashboard("startHourlyPolling");
      }
    });
  }

  if ($rangeButtons.length) {
    $rangeButtons.on("click", function () {
      var $btn = $(this);
      var hours = $btn.data("hours");
      $rangeButtons.removeClass("btn-secondary").addClass("btn-outline-secondary");
      $btn.removeClass("btn-outline-secondary").addClass("btn-secondary");
      if ($sensors.length) {
        var instance = $sensors.data("robotSensorsDashboard");
        if (instance) {
          instance.options.hourlyHours = hours;
          $sensors.robotSensorsDashboard("switchView", "hourly");
        }
      }
    });
  }

  // Fullscreen toggle
  var $fullscreenBtns = $("[data-fullscreen-toggle]");
  if ($fullscreenBtns.length) {
    $fullscreenBtns.on("click", function () {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(function () {});
        $(this).find("i").removeClass("bi-arrows-fullscreen").addClass("bi-fullscreen-exit");
      } else {
        document.exitFullscreen().catch(function () {});
        $(this).find("i").removeClass("bi-fullscreen-exit").addClass("bi-arrows-fullscreen");
      }
    });
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