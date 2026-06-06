/**
 * Robot control surface plugin.
 *
 * Responsibilities:
 * - Bind directional commands with delegated events via `/api/v1/move`.
 * - Handle touch gestures for swipe/press interactions.
 * - Poll telemetry and update overlay strip, battery bars, side panel, compass.
 * - Animate numeric value transitions.
 *
 * State is stored with `$.data()` for lightweight lifecycle management.
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    moveUrl: "/api/v1/move",
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

  function setHeading(degrees) {
    var $needle = $(".compass-needle");
    if (!$needle.length) return;
    var deg = coerceNumber(degrees) || 0;
    $needle.css({
      transform: "translate(-50%, -100%) rotate(" + deg + "deg)",
      transition: "transform 300ms ease",
    });
    var $badge = $("#heading-badge");
    if ($badge.length) $badge.text(Math.round(deg) + "\u00b0");
  }

  function normalizeSensorData(data) {
    if (!data) return null;
    return {
      temp: coerceNumber(data.temperature !== undefined ? data.temperature : data.temp),
      humidity: coerceNumber(data.humidity),
    };
  }

  /* ── Plugin ──────────────────────────────────────── */

  function ControlSurface(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);
    this.options.sensorsUrl = this.$root.data("sensorsUrl") || this.options.sensorsUrl;
    this.$camera = this.$root.find("#cameraZone");
    this.$gesture = this.$root.find("#gestureZone");
    this.$buttons = this.$root.find("[data-command]");

    // Telemetry strip overlay
    this.$temp = this.$root.find("#topTemp");
    this.$humidity = this.$root.find("#topHumidity");
    this.$battery = this.$root.find("#topBattery");
    this.$signal = this.$root.find("#topSignal");
    this.$time = this.$root.find("#topTime");

    // Side panel telemetry
    this.$speed = this.$root.find("#speed-value");
    this.$altitude = this.$root.find("#altitude-value");
    this.$batteryValue = this.$root.find("#battery-value");
    this.$batteryBars = this.$root.find("#battery-bars");
    this.$signalValue = this.$root.find("#signal-value");

    // Status dots
    this.$dots = {
      temp: this.$root.find("#topTempDot"),
      humidity: this.$root.find("#topHumidityDot"),
      battery: this.$root.find("#topBatteryDot"),
      signal: this.$root.find("#topSignalDot"),
    };
    this.lastUpdated = {};
    this.pollTimer = null;
    this.longPressTimer = null;
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
    this.moved = false;
  }

  ControlSurface.prototype.init = function () {
    var self = this;

    this.$root.attr("aria-busy", "true");
    this.$root.on("click.robotControlSurface", "[data-command]", function (event) {
      event.preventDefault();
      self.sendCommand($(this).data("command"));
    });

    this.$camera.add(this.$gesture)
      .on("touchstart.robotControlSurface", function (event) {
        self.onTouchStart(event);
      })
      .on("touchmove.robotControlSurface", function (event) {
        self.onTouchMove(event);
      })
      .on("touchend.robotControlSurface", function (event) {
        self.onTouchEnd(event);
      });

    this.pollTelemetry();
    this.pollTimer = window.setInterval(function () {
      self.pollTelemetry();
    }, this.options.pollIntervalMs);
    this.$root.attr("aria-busy", "false");
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
      self.$gesture.addClass("is-active");
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
    this.$gesture.removeClass("is-active");

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
    if (sensorData) {
      if (sensorData.temperature !== undefined) {
        animateValue(this.$temp, sensorData.temperature, "\u00b0C");
        this.markFresh("temp");
      }
      if (sensorData.humidity !== undefined) {
        animateValue(this.$humidity, sensorData.humidity, "%");
        this.markFresh("humidity");
      }
    }

    if (statusData) {
      if (statusData.battery !== undefined) {
        animateValue(this.$battery, statusData.battery, "%");
        animateValue(this.$batteryValue, statusData.battery, "%");
        updateBatteryBars(this.$batteryBars, statusData.battery);
        this.markFresh("battery");
      }
      if (statusData.signal !== undefined) {
        animateValue(this.$signal, statusData.signal, "%");
        animateValue(this.$signalValue, statusData.signal, "%");
        this.markFresh("signal");
      }
      if (statusData.speed !== undefined) {
        animateValue(this.$speed, statusData.speed, " km/h");
      }
      if (statusData.altitude !== undefined) {
        animateValue(this.$altitude, statusData.altitude, " m");
      }
      if (statusData.heading !== undefined) {
        setHeading(statusData.heading);
      }
    }

    this.$time.text(new Date().toLocaleTimeString());
  };

  ControlSurface.prototype.markFresh = function (key) {
    var $metric = this.$root.find("#metric" + key.charAt(0).toUpperCase() + key.slice(1));
    if ($metric.length) {
      $metric.removeClass("is-stale").attr("title", "Updated: just now");
    }
    if (this.$dots[key] && this.$dots[key].length) {
      this.$dots[key].attr("class", "status-dot status-dot--busy");
    }
    this.lastUpdated[key] = Date.now();
  };

  ControlSurface.prototype.markStale = function (key) {
    var $metric = this.$root.find("#metric" + key.charAt(0).toUpperCase() + key.slice(1));
    if ($metric.length) {
      $metric.addClass("is-stale").attr("title", "Stale data");
    }
    if (this.$dots[key] && this.$dots[key].length) {
      this.$dots[key].attr("class", "status-dot");
    }
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
          .fail(function () {
            $.each(["temp", "humidity"], function (_, k) { self.markStale(k); });
          });
        $.getJSON(self.options.statusUrl)
          .done(function (status) { self.updateTelemetry(status, null); })
          .fail(function () {
            $.each(["battery", "signal"], function (_, k) { self.markStale(k); });
          });
      });
  };

  ControlSurface.prototype.destroy = function () {
    if (this.pollTimer) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.clearLongPress();
    this.$camera.add(this.$gesture).off(".robotControlSurface");
    this.$root.off(".robotControlSurface");
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