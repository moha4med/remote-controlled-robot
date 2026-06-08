/**
 * Robot sensors dashboard plugin.
 *
 * Responsibilities:
 * - Load historical sensor data from `/api/v1/history/` on init.
 * - Render live temperature and humidity charts with Chart.js.
 * - Prefer Socket.IO updates when available.
 * - Fall back to polling `/api/v1/sensors/`.
 * - Animate numeric value transitions.
 * - Support real-time and hourly aggregated chart views.
 *
 * State is stored with `$.data()` for lightweight lifecycle management.
 */
(function ($, window, document) {
  "use strict";

  var DATA_KEY = "robotSensorsDashboard";
  var EVENT_NS = ".robotSensorsDashboard";

  var DEFAULTS = {
    sensorsUrl: "/api/v1/sensors/",
    logsUrl: "/api/v1/history/",
    hourlyUrl: "/api/v1/history/hourly",
    systemMetricsUrl: "/api/v1/system/metrics",
    pollIntervalMs: 2500,
    systemMetricsPollMs: 5000,
    points: 48,
    hourlyHours: 24,
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

  function formatUptime(seconds) {
    if (!seconds || seconds < 0) return "--";
    var d = Math.floor(seconds / 86400);
    var h = Math.floor((seconds % 86400) / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return d + "d " + h + "h " + m + "m";
    if (h > 0) return h + "h " + m + "m";
    return m + "m";
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

    // System metrics elements
    this.$sysCpu = this.$root.find("#sysCpuSensors");
    this.$sysMem = this.$root.find("#sysMemSensors");
    this.$sysDisk = this.$root.find("#sysDiskSensors");
    this.$sysCpuTemp = this.$root.find("#sysCpuTempSensors");
    this.$sysUptime = this.$root.find("#sysUptimeSensors");
    this.$sysStatus = this.$root.find("#sysStatusBadge");

    // Chart title/badge elements
    this.$tempTitle = this.$root.find("#tempChartTitle");
    this.$humidityTitle = this.$root.find("#humidityChartTitle");
    this.$tempBadge = this.$root.find("#tempChartBadge");
    this.$humidityBadge = this.$root.find("#humidityChartBadge");

    this.pollTimer = null;
    this.hourlyPollTimer = null;
    this.systemMetricsTimer = null;
    this.socketFallbackTimer = null;
    this.socket = null;
    this.usingSocket = false;
    this.chartInstances = {};
    this.history = {
      temp: [],
      humidity: [],
    };
    this.hourlyData = {
      temp: [],
      humidity: [],
      labels: [],
    };
    this.viewMode = "realtime";

    // Colors
    this.palette = {
      temp: getToken("--color-danger", "#ef4444"),
      tempFill: "rgba(239, 68, 68, 0.15)",
      humidity: getToken("--color-info", "#3b82f6"),
      humidityFill: "rgba(59, 130, 246, 0.15)",
      grid: getToken("--color-border-subtle", "rgba(148, 163, 184, 0.15)"),
      text: getToken("--color-text-muted", "#94a3b8"),
    };
  }

  SensorDashboard.prototype.init = function () {
    var self = this;
    this.$root.attr("aria-busy", "true");

    this.loadHistory(function () {
      self.createCharts();
      self.connectSocket();
      self.refresh();
      self.startPolling();
      self.refreshSystemMetrics();
      self.systemMetricsTimer = window.setInterval(function () {
        self.refreshSystemMetrics();
      }, self.options.systemMetricsPollMs);
      self.$root.attr("aria-busy", "false");
    });
  };

  /* ── History Loading ─────────────────────────────── */

  SensorDashboard.prototype.loadHistory = function (callback) {
    var self = this;
    $.getJSON(this.options.logsUrl)
      .done(function (logs) {
        if (!logs || !logs.length) {
          self.history.temp = [];
          self.history.humidity = [];
          if (callback) callback();
          return;
        }
        self.history.temp = [];
        self.history.humidity = [];
        $.each(logs, function (_, entry) {
          self.history.temp.push(coerceNumber(entry.temperature));
          self.history.humidity.push(coerceNumber(entry.humidity));
        });
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

  /* ── Chart.js Setup ──────────────────────────────── */

  SensorDashboard.prototype.getChartConfig = function (key, labels, data, isHourly) {
    var colors = this.palette;
    var color = key === "temp" ? colors.temp : colors.humidity;
    var fillColor = key === "temp" ? colors.tempFill : colors.humidityFill;
    var axisLabel = key === "temp" ? "Temperature (°C)" : "Humidity (%)";
    var yUnit = key === "temp" ? "°C" : "%";
    var xLabel = isHourly ? "Hour" : "Sample";
    var tooltipTitle = key === "temp" ? "Temperature" : "Humidity";

    return {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: axisLabel,
          data: data,
          borderColor: color,
          backgroundColor: fillColor,
          borderWidth: 2,
          pointRadius: isHourly ? 3 : 0,
          pointHoverRadius: 6,
          pointBackgroundColor: color,
          pointBorderColor: "#fff",
          pointBorderWidth: 2,
          fill: true,
          tension: 0.35,
          spanGaps: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        interaction: {
          intersect: false,
          mode: "index",
        },
        plugins: {
          legend: {
            display: true,
            position: "top",
            align: "end",
            labels: {
              color: colors.text,
              font: { size: 10, family: "'DM Sans', sans-serif", weight: "500" },
              boxWidth: 12,
              boxHeight: 3,
              borderRadius: 2,
              usePointStyle: true,
              pointStyle: "line",
              padding: 8,
            },
          },
          tooltip: {
            backgroundColor: getToken("--color-bg-panel-raised", "#1e293b"),
            titleColor: getToken("--color-text-primary", "#e2e8f0"),
            bodyColor: getToken("--color-text-secondary", "#cbd5e1"),
            footerColor: getToken("--color-text-muted", "#94a3b8"),
            borderColor: getToken("--color-border-subtle", "#334155"),
            borderWidth: 1,
            cornerRadius: 8,
            padding: { top: 8, bottom: 8, left: 12, right: 12 },
            titleFont: { size: 11, family: "'DM Sans', sans-serif", weight: "600" },
            bodyFont: { size: 12, family: "'JetBrains Mono', monospace", weight: "500" },
            footerFont: { size: 9, family: "'DM Sans', sans-serif" },
            displayColors: false,
            callbacks: {
              title: function (ctx) {
                if (!ctx.length) return "";
                var lbl = ctx[0].label;
                return isHourly ? "Hour: " + lbl : "Sample #" + lbl;
              },
              label: function (ctx) {
                if (ctx.parsed.y === null) return tooltipTitle + ": No data";
                return tooltipTitle + ": " + ctx.parsed.y.toFixed(1) + yUnit;
              },
              footer: function (ctx) {
                if (!ctx.length) return "";
                var val = ctx[0].parsed.y;
                if (val === null) return "";
                if (key === "temp") {
                  if (val > 40) return "⚠ High temperature";
                  if (val < 10) return "⚠ Low temperature";
                  return "✓ Normal range";
                } else {
                  if (val > 80) return "⚠ High humidity";
                  if (val < 20) return "⚠ Low humidity";
                  return "✓ Normal range";
                }
              },
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: xLabel,
              color: colors.text,
              font: { size: 10, family: "'DM Sans', sans-serif", weight: "600" },
              padding: { top: 8 },
            },
            grid: { color: colors.grid, drawBorder: false },
            ticks: {
              color: colors.text,
              font: { size: 9, family: "'JetBrains Mono', monospace" },
              maxTicksLimit: isHourly ? 12 : 8,
              maxRotation: 0,
            },
          },
          y: {
            title: {
              display: true,
              text: axisLabel,
              color: colors.text,
              font: { size: 10, family: "'DM Sans', sans-serif", weight: "600" },
              padding: { bottom: 8 },
            },
            grid: { color: colors.grid, drawBorder: false },
            ticks: {
              color: colors.text,
              font: { size: 9, family: "'JetBrains Mono', monospace" },
              callback: function (val) { return val + yUnit; },
            },
            beginAtZero: false,
          },
        },
      },
    };
  };

  SensorDashboard.prototype.createCharts = function () {
    var self = this;

    // Replace div containers with canvas elements
    $.each(this.$charts, function (key, $container) {
      if (!$container.length) return;
      var $canvas = $("<canvas></canvas>");
      $container.empty().append($canvas);
      self.$charts[key] = $canvas;
    });

    var tempCtx = this.$charts.temp[0];
    var humidityCtx = this.$charts.humidity[0];

    if (!tempCtx || !humidityCtx) return;

    // Build labels for real-time (sample indices)
    var rtLabels = this.history.temp.map(function (_, i) { return i + 1; });

    // Temperature chart
    this.chartInstances.temp = new window.Chart(tempCtx, this.getChartConfig(
      "temp", rtLabels, this.history.temp.slice(), false
    ));

    // Humidity chart
    this.chartInstances.humidity = new window.Chart(humidityCtx, this.getChartConfig(
      "humidity", rtLabels, this.history.humidity.slice(), false
    ));
  };

  SensorDashboard.prototype.updateCharts = function () {
    var self = this;
    var rtLabels = this.history.temp.map(function (_, i) { return i + 1; });

    $.each(this.chartInstances, function (key, chart) {
      if (!chart) return;
      chart.data.labels = rtLabels;
      chart.data.datasets[0].data = self.history[key].slice();
      chart.update("none");
    });
  };

  /* ── Hourly Data Loading ─────────────────────────── */

  SensorDashboard.prototype.loadHourlyData = function (callback) {
    var self = this;
    $.getJSON(this.options.hourlyUrl, { hours: this.options.hourlyHours })
      .done(function (data) {
        if (!data || !data.length) {
          self.hourlyData = { temp: [], humidity: [], labels: [] };
          if (callback) callback();
          return;
        }
        self.hourlyData.labels = [];
        self.hourlyData.temp = [];
        self.hourlyData.humidity = [];
        $.each(data, function (_, entry) {
          // "2024-01-01 14:00:00" → "14:00"
          var label = entry.hour ? (entry.hour.split(" ")[1] || "").slice(0, 5) || entry.hour : "";
          self.hourlyData.labels.push(label);
          self.hourlyData.temp.push(coerceNumber(entry.temperature));
          self.hourlyData.humidity.push(coerceNumber(entry.humidity));
        });
        if (callback) callback();
      })
      .fail(function () {
        self.hourlyData = { temp: [], humidity: [], labels: [] };
        if (callback) callback();
      });
  };

  /* ── View Mode Toggle ────────────────────────────── */

  SensorDashboard.prototype.switchView = function (mode) {
    var self = this;
    this.viewMode = mode;

    // Update titles and badges
    if (mode === "hourly") {
      if (this.$tempTitle.length) this.$tempTitle.text("Thermal Trend (Hourly Avg)");
      if (this.$humidityTitle.length) this.$humidityTitle.text("Humidity Trend (Hourly Avg)");
      if (this.$tempBadge.length) this.$tempBadge.text("Hourly").removeClass("bg-success").addClass("bg-info");
      if (this.$humidityBadge.length) this.$humidityBadge.text("Hourly").removeClass("bg-success").addClass("bg-info");
    } else {
      if (this.$tempTitle.length) this.$tempTitle.text("Thermal Trend");
      if (this.$humidityTitle.length) this.$humidityTitle.text("Humidity Trend");
      if (this.$tempBadge.length) this.$tempBadge.text("Live").removeClass("bg-info").addClass("bg-success");
      if (this.$humidityBadge.length) this.$humidityBadge.text("Live").removeClass("bg-info").addClass("bg-success");
    }

    if (mode === "hourly") {
      this.loadHourlyData(function () {
        $.each(self.chartInstances, function (key, chart) {
          if (!chart) return;
          chart.data.labels = self.hourlyData.labels.slice();
          chart.data.datasets[0].data = self.hourlyData[key].slice();
          chart.data.datasets[0].pointRadius = 3;
          chart.update();
        });
      });
    } else {
      var rtLabels = this.history.temp.map(function (_, i) { return i + 1; });
      $.each(this.chartInstances, function (key, chart) {
        if (!chart) return;
        chart.data.labels = rtLabels;
        chart.data.datasets[0].data = self.history[key].slice();
        chart.data.datasets[0].pointRadius = 0;
        chart.update();
      });
    }
  };

  SensorDashboard.prototype.startHourlyPolling = function () {
    var self = this;
    if (this.hourlyPollTimer) return;
    this.hourlyPollTimer = window.setInterval(function () {
      if (self.viewMode === "hourly") {
        self.loadHourlyData(function () {
          $.each(self.chartInstances, function (key, chart) {
            if (!chart) return;
            chart.data.labels = self.hourlyData.labels.slice();
            chart.data.datasets[0].data = self.hourlyData[key].slice();
            chart.update("none");
          });
        });
      }
    }, 60000);
  };

  /* ── System Metrics Polling ──────────────────────── */

  SensorDashboard.prototype.refreshSystemMetrics = function () {
    var self = this;
    $.getJSON(this.options.systemMetricsUrl)
      .done(function (data) {
        self.updateSystemMetrics(data);
      });
    return this;
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
      if (self.$sysStatus.length) {
        self.$sysStatus
          .html('<span class="d-inline-block rounded-circle bg-success me-1" style="width:6px;height:6px"></span> Live')
          .removeClass("bg-danger bg-warning")
          .addClass("bg-success bg-opacity-25 text-success border border-success border-opacity-25");
      }
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
      if (self.$sysStatus.length) {
        self.$sysStatus
          .html('<span class="d-inline-block rounded-circle bg-danger me-1" style="width:6px;height:6px"></span> Disconnected')
          .removeClass("bg-success bg-warning")
          .addClass("bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25");
      }
    });

    this.socket.on("system:update", function (data) {
      self.updateSystemMetrics(data);
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

    // Only update chart in realtime mode
    if (this.viewMode === "realtime" && this.chartInstances[key]) {
      var chart = this.chartInstances[key];
      var rtLabels = this.history.temp.map(function (_, i) { return i + 1; });
      chart.data.labels = rtLabels;
      chart.data.datasets[0].data = this.history[key].slice();
      chart.update("none");
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

  SensorDashboard.prototype.updateSystemMetrics = function (data) {
    if (!data) return this;

    if (data.cpu_usage !== undefined && this.$sysCpu.length) {
      this.$sysCpu.text(Number(data.cpu_usage).toFixed(0) + "%");
    }
    if (data.memory_usage !== undefined && this.$sysMem.length) {
      this.$sysMem.text(Number(data.memory_usage).toFixed(0) + "%");
    }
    if (data.disk_usage !== undefined && this.$sysDisk.length) {
      this.$sysDisk.text(Number(data.disk_usage).toFixed(0) + "%");
    }
    if (data.cpu_temperature !== undefined && this.$sysCpuTemp.length) {
      this.$sysCpuTemp.text(Number(data.cpu_temperature).toFixed(0) + "\u00b0C");
    }
    if (data.uptime !== undefined && this.$sysUptime.length) {
      this.$sysUptime.text(formatUptime(data.uptime));
    }
    if (this.$sysStatus.length) {
      this.$sysStatus
        .html('<span class="d-inline-block rounded-circle bg-success me-1" style="width:6px;height:6px"></span> Live')
        .removeClass("bg-danger bg-warning")
        .addClass("bg-success bg-opacity-25 text-success border border-success border-opacity-25");
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

  /* ── Lifecycle ───────────────────────────────────── */

  SensorDashboard.prototype.destroy = function () {
    this.stopPolling();
    if (this.hourlyPollTimer) {
      window.clearInterval(this.hourlyPollTimer);
      this.hourlyPollTimer = null;
    }
    if (this.systemMetricsTimer) {
      window.clearInterval(this.systemMetricsTimer);
      this.systemMetricsTimer = null;
    }
    this.clearSocketFallback();
    $(window).off(EVENT_NS);
    if (this.socket && typeof this.socket.disconnect === "function") {
      this.socket.disconnect();
      this.socket = null;
    }
    $.each(this.chartInstances, function (_, chart) {
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