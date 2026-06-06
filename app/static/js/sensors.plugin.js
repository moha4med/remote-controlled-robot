/**
 * Robot sensors dashboard plugin.
 *
 * Responsibilities:
 * - Load historical sensor data from `/api/v1/logs/sensors` on init.
 * - Render live temperature and humidity charts with uPlot.
 * - Prefer Socket.IO updates when available.
 * - Fall back to polling `/api/v1/sensors/`.
 * - Animate numeric value transitions.
 *
 * State is stored with `$.data()` for lightweight lifecycle management.
 */
(function ($, window, document) {
  "use strict";

  var DATA_KEY = "robotSensorsDashboard";
  var EVENT_NS = ".robotSensorsDashboard";

  var DEFAULTS = {
    sensorsUrl: "/api/v1/sensors/",
    logsUrl: "/api/v1/logs/sensors",
    pollIntervalMs: 2500,
    points: 48,
    socketEnabled: true,
    socketUrl: null,
    socketEvent: "sensor:update",
    socketErrorEvent: "sensor:error",
    socketTimeoutMs: 5000,
  };

  /* ── Helpers ─────────────────────────────────────── */

  function getToken(name, fallback) {
    var value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function colorToRgba(color, alpha) {
    var probe = document.createElement("span");
    probe.style.color = color;
    document.body.appendChild(probe);
    var computed = window.getComputedStyle(probe).color;
    document.body.removeChild(probe);
    var parts = computed.match(/\d+(\.\d+)?/g);
    if (!parts || parts.length < 3) return "rgba(20, 184, 166, " + alpha + ")";
    return "rgba(" + parts[0] + ", " + parts[1] + ", " + parts[2] + ", " + alpha + ")";
  }

  function coerceNumber(value) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function formatValue(value, suffix) {
    var n = coerceNumber(value);
    if (n === null) return "--";
    suffix = suffix || "";
    return n.toFixed(1) + suffix;
  }

  function normalizeSensorData(data) {
    if (!data) return null;
    return {
      temp: coerceNumber(data.temperature !== undefined ? data.temperature : data.temp),
      humidity: coerceNumber(data.humidity),
      timestamp: data.timestamp || Date.now(),
    };
  }

  function buildHistory(values, length) {
    var h = values.slice(Math.max(values.length - length, 0));
    while (h.length < length) h.unshift(null);
    return h;
  }

  /* ── Plugin ──────────────────────────────────────── */

  function SensorDashboard(element, options) {
    this.$root = $(element);
    this.options = $.extend(true, {}, DEFAULTS, options);
    this.$charts = {
      temp: this.$root.find("#tempChart"),
      humidity: this.$root.find("#humidityChart"),
    };
    this.$values = {
      temp: this.$root.find("#tempValue, #tempValueCard"),
      humidity: this.$root.find("#humidityValue, #humidityValueCard"),
    };
    this.$sync = this.$root.find("#sensorSync");
    this.pollTimer = null;
    this.socketFallbackTimer = null;
    this.socket = null;
    this.usingSocket = false;
    this.charts = {};
    this.history = {
      temp: [],
      humidity: [],
    };
    this.palette = {
      temp: getToken("--color-danger", getToken("--accent", "#14b8a6")),
      humidity: getToken("--color-info", getToken("--accent", "#38bdf8")),
      textSecondary: getToken("--color-text-secondary", "#94a3b8"),
    };
  }

  SensorDashboard.prototype.init = function () {
    var self = this;
    this.$root.attr("aria-busy", "true");

    // Load historical data first, then create charts
    this.loadHistory(function () {
      $.each(self.$charts, function (key, $canvas) {
        if ($canvas.length && window.uPlot) {
          self.charts[key] = self.createChart($canvas[0], key);
        }
      });
      self.bindResize();
      self.connectSocket();
      self.refresh();
      self.startPolling();
      self.$root.attr("aria-busy", "false");
    });
  };

  /* ── History Loading ─────────────────────────────── */

  SensorDashboard.prototype.loadHistory = function (callback) {
    var self = this;
    $.getJSON(this.options.logsUrl)
      .done(function (logs) {
        if (!logs || !logs.length) {
          // Fall back to empty history
          self.history.temp = [];
          self.history.humidity = [];
          if (callback) callback();
          return;
        }
        // Extract temp and humidity arrays
        self.history.temp = [];
        self.history.humidity = [];
        $.each(logs, function (_, entry) {
          if (entry.temperature !== null && entry.temperature !== undefined) {
            self.history.temp.push(entry.temperature);
          }
          if (entry.humidity !== null && entry.humidity !== undefined) {
            self.history.humidity.push(entry.humidity);
          }
        });
        // Trim to max points
        self.history.temp = self.history.temp.slice(-self.options.points);
        self.history.humidity = self.history.humidity.slice(-self.options.points);
        if (callback) callback();
      })
      .fail(function () {
        self.history.temp = [];
        self.history.humidity = [];
        if (callback) callback();
      });
  };

  /* ── Chart Setup ─────────────────────────────────── */

  SensorDashboard.prototype.createChart = function (container, key) {
    var values = this.history[key].length
      ? this.history[key].slice(0)
      : new Array(this.options.points).fill(null);
    while (values.length < this.options.points) values.unshift(null);

    var xData = this.getXData(values);
    var seriesColor = this.palette[key];
    var fillColor = colorToRgba(seriesColor, 0.18);
    var gridColor = colorToRgba(this.palette.textSecondary, 0.16);

    return new window.uPlot({
      width: container.clientWidth || 520,
      height: container.clientHeight || 220,
      class: "sensor-uplot",
      legend: { show: false },
      cursor: { show: false },
      scales: { x: { time: false }, y: { auto: true } },
      series: [
        { label: "sample" },
        {
          label: key,
          stroke: seriesColor,
          fill: fillColor,
          width: 2,
          spanGaps: true,
        },
      ],
      axes: [
        { show: false, grid: { show: false } },
        { show: false, grid: { stroke: gridColor } },
      ],
    }, [xData, values], container);
  };

  SensorDashboard.prototype.getXData = function (values) {
    return values.map(function (_, i) { return i + 1; });
  };

  SensorDashboard.prototype.resizeCharts = function () {
    var self = this;
    $.each(this.charts, function (key, chart) {
      var container = chart && chart.root && chart.root.parentNode;
      if (!container) return;
      chart.setSize({
        width: container.clientWidth || 520,
        height: container.clientHeight || 220,
      });
    });
  };

  SensorDashboard.prototype.bindResize = function () {
    var self = this;
    $(window).on("resize" + EVENT_NS, function () { self.resizeCharts(); });
  };

  /* ── Socket.IO ───────────────────────────────────── */

  SensorDashboard.prototype.connectSocket = function () {
    var self = this;
    if (!this.options.socketEnabled || !window.io) return this;

    this.socket = window.io(this.options.socketUrl || undefined, {
      transports: ["websocket", "polling"],
    });

    this.socket.on("connect", function () {
      self.usingSocket = true;
      self.stopPolling();
      self.clearSocketFallback();
    });

    this.socket.on(this.options.socketEvent, function (data) {
      self.updateValues(data);
    });

    this.socket.on(this.options.socketErrorEvent, function () {
      self.usingSocket = false;
      self.startPolling();
    });

    this.socket.on("disconnect", function () {
      self.usingSocket = false;
      self.startPolling();
    });

    this.socketFallbackTimer = window.setTimeout(function () {
      if (!self.usingSocket) self.startPolling();
    }, this.options.socketTimeoutMs);
  };

  SensorDashboard.prototype.clearSocketFallback = function () {
    if (this.socketFallbackTimer) {
      window.clearTimeout(this.socketFallbackTimer);
      this.socketFallbackTimer = null;
    }
  };

  /* ── Data Push ───────────────────────────────────── */

  SensorDashboard.prototype.pushValue = function (key, value) {
    var number = coerceNumber(value);
    if (number === null) return this;
    this.history[key].push(number);
    this.history[key] = this.history[key].slice(-this.options.points);
    if (this.charts[key]) {
      var values = this.history[key].slice(0);
      var xData = this.getXData(values);
      // Pad with nulls at the front if needed
      while (values.length < this.options.points) {
        values.unshift(null);
        xData.unshift(xData[0] ? xData[0] - 1 : 0);
      }
      this.charts[key].setData([xData, values]);
    }
    return this;
  };

  SensorDashboard.prototype.updateValues = function (data) {
    var sensors = normalizeSensorData(data);
    if (!sensors) return this;

    if (sensors.temp !== null) {
      this.$values.temp.text(formatValue(sensors.temp, "\u00b0C"));
      this.pushValue("temp", sensors.temp);
    }
    if (sensors.humidity !== null) {
      this.$values.humidity.text(formatValue(sensors.humidity, "%"));
      this.pushValue("humidity", sensors.humidity);
    }
    if (this.$sync.length && (sensors.temp !== null || sensors.humidity !== null)) {
      this.$sync.text(new Date().toLocaleTimeString());
    }
    return this;
  };

  SensorDashboard.prototype.refresh = function () {
    var self = this;
    $.getJSON(this.options.sensorsUrl)
      .done(function (data) { self.updateValues(data); })
      .always(function () { self.$root.attr("aria-busy", "false"); });
  };

  SensorDashboard.prototype.startPolling = function () {
    var self = this;
    if (this.pollTimer) return;
    this.pollTimer = window.setInterval(function () { self.refresh(); }, this.options.pollIntervalMs);
  };

  SensorDashboard.prototype.stopPolling = function () {
    if (this.pollTimer) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  };

  SensorDashboard.prototype.destroy = function () {
    this.stopPolling();
    this.clearSocketFallback();
    $(window).off(EVENT_NS);
    if (this.socket && typeof this.socket.disconnect === "function") {
      this.socket.disconnect();
      this.socket = null;
    }
    $.each(this.charts, function (_, chart) {
      if (chart && typeof chart.destroy === "function") chart.destroy();
    });
    this.$root.removeData(DATA_KEY);
  };

  $.fn.robotSensorsDashboard = function (methodOrOptions) {
    var args = Array.prototype.slice.call(arguments, 1);
    return this.each(function () {
      var instance = $.data(this, DATA_KEY);
      if (!instance) {
        instance = new SensorDashboard(this, methodOrOptions);
        $.data(this, DATA_KEY, instance);
        instance.init();
        return;
      }
      if (typeof methodOrOptions === "string" && typeof instance[methodOrOptions] === "function") {
        instance[methodOrOptions].apply(instance, args);
      }
    });
  };
})(jQuery, window, document);