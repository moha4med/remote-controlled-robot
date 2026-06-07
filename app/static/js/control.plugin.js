/**
 * Robot control surface plugin.
 *
 * Responsibilities:
 * - Bind directional commands via `/api/v1/move`.
 * - Handle touch gestures for swipe/press interactions.
 * - Poll telemetry and update overlay strip, battery bars, side panel.
 * - Animate numeric value transitions.
 * - Mobile: fullscreen camera by default, slide-up controls drawer.
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    moveUrl: "/api/v1/robot/move",
    sensorsUrl: "/api/v1/sensors/",
    statusUrl: "/api/v1/status",
    pollIntervalMs: 3000,
  };

  /* ── Helpers ─────────────────────────────────────── */

  function coerceNumber(value) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function animateValue($el, newVal, suffix, duration) {
    if (!$el || !$el.length) return;
    var current = parseFloat($el.data("value")) || 0;
    var target = coerceNumber(newVal);
    if (target === null) {
      $el.text("--" + (suffix || ""));
      return;
    }
    suffix = suffix || "";
    duration = duration || 300;
    $({ val: current }).animate({ val: target }, {
      duration: duration,
      easing: "swing",
      step: function () {
        $el.text(Number(this.val).toFixed(0) + suffix);
      },
      complete: function () {
        $el.text(target + suffix);
        $el.data("value", target);
      },
    });
  }

  function updateBatteryBars($container, percent) {
    if (!$container || !$container.length) return;
    var $bars = $container.find(".battery-bar");
    if (!$bars.length) return;
    var total = $bars.length;
    var active = Math.round((percent / 100) * total);
    $bars.each(function (i) {
      $(this).toggleClass("is-active", i < active);
    });
  }

  function updateText($el, text) {
    if ($el && $el.length) $el.text(text);
  }

  /* ── Plugin ──────────────────────────────────────── */

  function ControlSurface(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);
    this.options.sensorsUrl = this.$root.data("sensorsUrl") || this.options.sensorsUrl;

    // Mobile elements
    this.$mobileCamera = this.$root.find(".mobile-camera-wrap");
    this.$mobileDrawer = this.$root.find("#mobileControls");
    this.$mobileToggle = this.$root.find(".mobile-toggle-controls");

    // Desktop elements
    this.$buttons = this.$root.find("[data-command]");

    // Overlay telemetry (desktop)
    this.$temp = this.$root.find("#topTemp");
    this.$humidity = this.$root.find("#topHumidity");
    this.$battery = this.$root.find("#topBattery");
    this.$signal = this.$root.find("#topSignal");
    this.$time = this.$root.find("#topTime");

    // Overlay telemetry (mobile)
    this.$tempMobile = this.$root.find("#topTempMobile");
    this.$humidityMobile = this.$root.find("#topHumidityMobile");
    this.$batteryMobile = this.$root.find("#topBatteryMobile");
    this.$signalMobile = this.$root.find("#topSignalMobile");
    this.$timeMobile = this.$root.find("#topTimeMobile");

    // Side panel telemetry (desktop)
    this.$speed = this.$root.find("#speed-value");
    this.$batteryValue = this.$root.find("#battery-value");
    this.$batteryBars = this.$root.find("#battery-bars");
    this.$signalValue = this.$root.find("#signal-value");
    this.$robotState = this.$root.find("#robot-state");

    // Mobile telemetry
    this.$speedMobile = this.$root.find("#speed-value-mobile");
    this.$batteryValueMobile = this.$root.find("#battery-value-mobile");
    this.$signalValueMobile = this.$root.find("#signal-value-mobile");
    this.$robotStateMobile = this.$root.find("#robot-state-mobile");

    this.pollTimer = null;
    this.longPressTimer = null;
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
    this.moved = false;
  }

  ControlSurface.prototype.init = function () {
    var self = this;

    // Command buttons
    this.$root.on("click.robotControlSurface", "[data-command]", function (event) {
      event.preventDefault();
      self.sendCommand($(this).data("command"));
    });

    // Mobile drawer toggle
    if (this.$mobileToggle.length) {
      this.$mobileToggle.on("click.robotControlSurface", function () {
        self.$mobileDrawer.toggleClass("show");
      });
    }

    // Touch gestures on camera
    this.$mobileCamera.add(this.$root.find(".camera-wrap"))
      .on("touchstart.robotControlSurface", function (event) {
        self.onTouchStart(event);
      })
      .on("touchmove.robotControlSurface", function (event) {
        self.onTouchMove(event);
      })
      .on("touchend.robotControlSurface", function (event) {
        self.onTouchEnd(event);
      });

    // Start polling
    this.pollTelemetry();
    this.pollTimer = window.setInterval(function () {
      self.pollTelemetry();
    }, this.options.pollIntervalMs);

    return this;
  };

  /* ── Touch / Gesture ─────────────────────────────── */

  ControlSurface.prototype.onTouchStart = function (event) {
    var touch = event.originalEvent.touches[0];
    var self = this;
    this.startX = touch.clientX;
    this.startY = touch.clientY;
    this.startTime = Date.now();
    this.moved = false;
    this.clearLongPress();
    this.longPressTimer = window.setTimeout(function () {
      self.sendCommand("stop");
    }, 650);
  };

  ControlSurface.prototype.onTouchMove = function (event) {
    var touch = event.originalEvent.touches[0];
    var dx = Math.abs(touch.clientX - this.startX);
    var dy = Math.abs(touch.clientY - this.startY);
    if (dx > 8 || dy > 8) {
      this.moved = true;
      this.clearLongPress();
    }
  };

  ControlSurface.prototype.onTouchEnd = function (event) {
    var touch = event.originalEvent.changedTouches[0];
    var dx = touch.clientX - this.startX;
    var dy = touch.clientY - this.startY;
    var duration = Date.now() - this.startTime;
    var threshold = 40;

    this.clearLongPress();

    if (Math.abs(dx) > threshold || Math.abs(dy) > threshold) {
      this.sendCommand(
        Math.abs(dx) > Math.abs(dy)
          ? (dx > 0 ? "right" : "left")
          : (dy > 0 ? "backward" : "forward")
      );
      return;
    }
    if (!this.moved && duration < 250) {
      this.sendCommand("stop");
    }
  };

  ControlSurface.prototype.clearLongPress = function () {
    if (this.longPressTimer) {
      window.clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
  };

  ControlSurface.prototype.sendCommand = function (command) {
    $.ajax({
      url: this.options.moveUrl,
      method: "POST",
      data: { direction: command },
    });
  };

  /* ── Telemetry ───────────────────────────────────── */

  ControlSurface.prototype.updateTelemetry = function (statusData, sensorData) {
    var self = this;

    if (sensorData) {
      if (sensorData.temperature !== undefined) {
        animateValue(this.$temp, sensorData.temperature, "\u00b0C");
        updateText(this.$tempMobile, (sensorData.temperature !== null ? sensorData.temperature : "--") + "\u00b0C");
      }
      if (sensorData.humidity !== undefined) {
        animateValue(this.$humidity, sensorData.humidity, "%");
        updateText(this.$humidityMobile, (sensorData.humidity !== null ? sensorData.humidity : "--") + "%");
      }
    }

    if (statusData) {
      if (statusData.battery !== undefined) {
        animateValue(this.$battery, statusData.battery, "%");
        animateValue(this.$batteryValue, statusData.battery, "%");
        updateText(this.$batteryMobile, statusData.battery + "%");
        updateBatteryBars(this.$batteryBars, statusData.battery);
      }
      if (statusData.signal !== undefined) {
        animateValue(this.$signal, statusData.signal, "%");
        animateValue(this.$signalValue, statusData.signal, "%");
        updateText(this.$signalMobile, statusData.signal + "%");
      }
      if (statusData.state !== undefined) {
        updateText(this.$robotState, statusData.state);
        updateText(this.$robotStateMobile, statusData.state);
      }
    }

    var timeStr = new Date().toLocaleTimeString();
    updateText(this.$time, timeStr);
    updateText(this.$timeMobile, timeStr);
  };

  ControlSurface.prototype.pollTelemetry = function () {
    var self = this;
    $.when(
      $.getJSON(this.options.sensorsUrl),
      $.getJSON(this.options.statusUrl)
    )
      .done(function (sensorsResponse, statusResponse) {
        var sensors = sensorsResponse[0] || sensorsResponse;
        var status = statusResponse[0] || statusResponse;
        self.updateTelemetry(status, sensors);
      })
      .fail(function () {
        $.getJSON(self.options.sensorsUrl)
          .done(function (sensors) { self.updateTelemetry(null, sensors); })
          .fail(function () {});
        $.getJSON(self.options.statusUrl)
          .done(function (status) { self.updateTelemetry(status, null); })
          .fail(function () {});
      });
  };

  ControlSurface.prototype.destroy = function () {
    if (this.pollTimer) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.clearLongPress();
    this.$root.off(".robotControlSurface");
    this.$mobileCamera.off(".robotControlSurface");
    this.$root.removeData("robotControlSurface");
  };

  $.fn.robotControlSurface = function (methodOrOptions) {
    var args = Array.prototype.slice.call(arguments, 1);
    return this.each(function () {
      var instance = $.data(this, "robotControlSurface");
      if (!instance) {
        instance = new ControlSurface(this, methodOrOptions);
        $.data(this, "robotControlSurface", instance);
        instance.init();
        return;
      }
      if (typeof methodOrOptions === "string" && typeof instance[methodOrOptions] === "function") {
        instance[methodOrOptions].apply(instance, args);
      }
    });
  };
})(jQuery);