$(function () {
  if (window.feather) {
    feather.replace({ width: 18, height: 18 });
  }

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

  $(".tab-btn").on("click", function () {
    var $btn = $(this);
    var target = $btn.data("target");
    if (!target) {
      return;
    }
    $btn.closest(".tab-group").find(".tab-btn").removeClass("active");
    $btn.addClass("active");
    $(target).siblings(".tab-panel").removeClass("is-active").hide();
    $(target).addClass("is-active").fadeIn(150);
  });

  function updateBatteryBars($slider, value) {
    var target = $slider.data("bars");
    if (!target) {
      return;
    }
    var $bars = $(target).find(".battery-bar");
    if (!$bars.length) {
      return;
    }
    var totalBars = $bars.length;
    var activeBars = Math.round((value / 100) * totalBars);
    $bars.each(function (index) {
      var isActive = index < activeBars;
      $(this).toggleClass("bg-teal-500", isActive);
      $(this).toggleClass("shadow-[0_0_8px_rgba(20,184,166,0.45)]", isActive);
      $(this).toggleClass("bg-[rgba(148,163,184,0.55)]", !isActive);
    });
  }

  $(".param-slider").on("input", function () {
    var $slider = $(this);
    var value = parseInt($slider.val(), 10) || 0;
    var pct = value + "%";
    $slider.css("--fill", pct);
    var target = $slider.data("display");
    if (target) {
      $(target).text(pct);
    }
    updateBatteryBars($slider, value);
  });

  $(".param-slider").trigger("input");

  var $fullscreenPrompt = $("#fullscreenPrompt");
  var $fullscreenButton = $("#enterFullscreen");

  function enterFullscreen() {
    var root = document.documentElement;
    if (!root.requestFullscreen) {
      return;
    }

    root.requestFullscreen()
      .then(function () {
        if (screen.orientation && screen.orientation.lock) {
          return screen.orientation.lock("landscape").catch(function () {
            return null;
          });
        }
        return null;
      })
      .then(function () {
        $fullscreenPrompt.addClass("is-hidden");
      })
      .catch(function () {
        $fullscreenPrompt.addClass("is-hidden");
      });
  }

  if ($fullscreenButton.length) {
    $fullscreenButton.on("click", function () {
      enterFullscreen();
    });
  }

  var $chromeToggle = $("#mobileChromeToggle");
  var $mobileSidebar = $("#mobileSidebar");
  var $mobilePanelHeader = $("#mobilePanelHeader");

  function setMobileChromeState(isOpen) {
    if ($mobileSidebar.length) {
      $mobileSidebar.toggleClass("hidden", !isOpen);
    }

    if ($mobilePanelHeader.length) {
      $mobilePanelHeader.toggleClass("hidden", !isOpen);
    }
  }

  if ($chromeToggle.length) {
    $chromeToggle.on("click", function () {
      var isOpen = !$chromeToggle.hasClass("is-open");
      $chromeToggle.toggleClass("is-open", isOpen);
      setMobileChromeState(isOpen);
      $chromeToggle.attr("aria-expanded", isOpen ? "true" : "false");
      $chromeToggle.attr("aria-label", isOpen ? "Hide navigation" : "Show navigation");
    });
  }

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
