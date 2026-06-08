/**
 * Robot dashboard plugin.
 *
 * Responsibilities:
 * - Poll `/api/v1/status` every 2s for live telemetry.
 * - Poll `/api/v1/system/metrics` every 5s for host metrics.
 * - Receive system metrics via SocketIO `system:update` events.
 * - Animate numeric value transitions.
 * - Handle image capture via `/api/v1/captures/`.
 * - Display capture gallery with thumbnails and full-size preview.
 * - Delegate quick-action button clicks to `/api/v1/events`.
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    statusUrl: "/api/v1/status",
    systemMetricsUrl: "/api/v1/system/metrics",
    eventsUrl: "/api/v1/events",
    capturesUrl: "/api/v1/captures/",
    pollIntervalMs: 2000,
    systemMetricsPollMs: 5000,
    galleryPollMs: 5000,
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

  function formatTimestamp(isoString) {
    if (!isoString) return "";
    var d = new Date(isoString);
    return d.toLocaleTimeString();
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

  function DashboardBoard(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);

    // Telemetry elements (camera metrics bar)
    this.$battery = this.$root.find("#batteryValue, #batteryValueTel");
    this.$signal = this.$root.find("#signal, #signalTel");
    this.$temp = this.$root.find("#temp, #tempTel");
    this.$mode = this.$root.find("#modeValue");
    this.$timestamp = this.$root.find("#dashboardTimestamp, #camTime");

    // System metrics elements
    this.$sysCpu = this.$root.find("#sysCpu");
    this.$sysMem = this.$root.find("#sysMem");
    this.$sysDisk = this.$root.find("#sysDisk");
    this.$sysCpuTemp = this.$root.find("#sysCpuTemp");
    this.$sysUptime = this.$root.find("#sysUptime");
    this.$systemStatus = this.$root.find("#systemStatus");
    this.$sysStatusHost = this.$root.find("#sysStatusHost");

    // Capture elements
    this.$btnCapture = this.$root.find("#btnCapture");
    this.$captureStatus = this.$root.find("#captureStatus");
    this.$captureCount = this.$root.find("#captureCount");
    this.$gallery = this.$root.find("#captureGallery");
    this.$galleryEmpty = this.$root.find("#galleryEmpty");
    this.$cameraPreview = this.$root.find("#cameraPreviewImg");

    // Quick actions
    this.$actions = this.$root.find("[data-action]");

    this.timerId = null;
    this.galleryTimerId = null;
    this.systemMetricsTimerId = null;
    this.knownCaptureIds = {};
    this.socket = null;
  }

  DashboardBoard.prototype.init = function () {
    var self = this;

    this.$root.attr("aria-busy", "true");

    // Quick actions
    this.$root.on("click.robotDashboardBoard", "[data-action]", function (event) {
      event.preventDefault();
      self.sendAction($(this).data("action"));
    });

    // Capture button
    if (this.$btnCapture.length) {
      this.$btnCapture.on("click.robotDashboardBoard", function () {
        self.triggerCapture();
      });
    }

    // Start polling
    this.refresh();
    this.timerId = window.setInterval(function () {
      self.refresh();
    }, this.options.pollIntervalMs);

    // Load gallery initially and poll for updates
    this.loadGallery();
    this.galleryTimerId = window.setInterval(function () {
      self.loadGallery();
    }, this.options.galleryPollMs);

    // Connect SocketIO
    this.connectSocket();

    // Poll system metrics on init and periodically
    this.refreshSystemMetrics();
    this.systemMetricsTimerId = window.setInterval(function () {
      self.refreshSystemMetrics();
    }, this.options.systemMetricsPollMs);

    this.$root.attr("aria-busy", "false");
    return this;
  };

  /* ── System Metrics Polling ──────────────────────── */

  DashboardBoard.prototype.refreshSystemMetrics = function () {
    var self = this;
    $.getJSON(this.options.systemMetricsUrl)
      .done(function (data) {
        self.updateSystemMetrics(data);
      });
    return this;
  };

  /* ── Socket.IO ───────────────────────────────────── */

  DashboardBoard.prototype.connectSocket = function () {
    var self = this;
    if (!window.io) return;

    this.socket = window.io(undefined, {
      transports: ["websocket", "polling"],
    });

    this.socket.on("connect", function () {
      if (self.$systemStatus.length) {
        self.$systemStatus
          .html('<span class="status-pulse__dot"></span><span class="status-pulse__label">Live</span>');
      }
      if (self.$sysStatusHost.length) {
        self.$sysStatusHost
          .html('<span class="d-inline-block rounded-circle bg-status-ok me-1" style="width:5px;height:5px"></span> Live');
      }
    });

    this.socket.on("system:update", function (data) {
      self.updateSystemMetrics(data);
    });

    this.socket.on("disconnect", function () {
      if (self.$systemStatus.length) {
        self.$systemStatus
          .html('<span class="status-pulse__dot status-pulse__dot--off"></span><span class="status-pulse__label">Disconnected</span>');
      }
      if (self.$sysStatusHost.length) {
        self.$sysStatusHost
          .html('<span class="d-inline-block rounded-circle bg-status-danger me-1" style="width:5px;height:5px"></span> Offline');
      }
    });
  };

  /* ── System Metrics ───────────────────────────────── */

  DashboardBoard.prototype.updateSystemMetrics = function (data) {
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
    return this;
  };

  /* ── Telemetry ───────────────────────────────────── */

  DashboardBoard.prototype.refresh = function () {
    var self = this;
    $.getJSON(this.options.statusUrl)
      .done(function (data) {
        self.updateStatus(data);
      })
      .fail(function () {
        self.$root.attr("aria-busy", "false");
      });
    return this;
  };

  DashboardBoard.prototype.updateStatus = function (data) {
    if (!data) return this;

    if (data.battery !== undefined) {
      animateValue(this.$battery, data.battery, "%");
    }
    if (data.signal !== undefined) {
      animateValue(this.$signal, data.signal, "%");
    }
    if (data.mode !== undefined) {
      this.$mode.text(data.mode);
    }
    if (data.temp !== undefined) {
      this.$temp.text(data.temp + "\u00b0C");
    }
    var timeStr = new Date().toLocaleTimeString();
    this.$timestamp.text(timeStr);
    return this;
  };

  DashboardBoard.prototype.sendAction = function (action) {
    $.ajax({
      url: this.options.eventsUrl,
      method: "POST",
      data: { action: action },
    });
    return this;
  };

  /* ── Capture ──────────────────────────────────────── */

  DashboardBoard.prototype.triggerCapture = function () {
    var self = this;

    this.$btnCapture.prop("disabled", true);
    this.$captureStatus
      .html('<i class="bi bi-arrow-repeat spin"></i> Capturing...')
      .removeClass("bg-success bg-danger")
      .addClass("bg-info text-dark");

    $.ajax({
      url: this.options.capturesUrl,
      method: "POST",
      success: function (capture) {
        self.$captureStatus
          .html('<i class="bi bi-check-circle me-1"></i> Captured!')
          .removeClass("bg-info bg-danger")
          .addClass("bg-success");

        self.loadGallery();

        if (self.$cameraPreview.length && capture.thumbnail_url) {
          self.$cameraPreview.attr("src", capture.thumbnail_url + "?t=" + Date.now());
        }
      },
      error: function () {
        self.$captureStatus
          .html('<i class="bi bi-exclamation-triangle me-1"></i> Failed')
          .removeClass("bg-info bg-success")
          .addClass("bg-danger");
      },
      complete: function () {
        self.$btnCapture.prop("disabled", false);
        window.setTimeout(function () {
          self.$captureStatus
            .html('<i class="bi bi-check-circle me-1"></i> Ready')
            .removeClass("bg-info bg-danger")
            .addClass("bg-success");
        }, 3000);
      },
    });
  };

  /* ── Gallery ──────────────────────────────────────── */

  DashboardBoard.prototype.loadGallery = function () {
    var self = this;
    $.getJSON(this.options.capturesUrl)
      .done(function (data) {
        var items = data.items || data;
        if (Array.isArray(items)) {
          self.renderGallery(items);
        }
      });
  };

  DashboardBoard.prototype.renderGallery = function (captures) {
    if (!captures || !captures.length) {
      this.$gallery.empty().append(
        '<div class="gallery-empty" id="galleryEmpty"><i class="bi bi-camera"></i><span>No captures yet</span></div>'
      );
      this.$captureCount.text("0");
      return this;
    }

    this.$captureCount.text(captures.length);

    var html = "";
    var self = this;
    $.each(captures, function (_, cap) {
      self.knownCaptureIds[cap.id] = true;
      var thumbUrl = cap.thumbnail_url || cap.url;
      html +=
        '<div class="capture-card" data-id="' + cap.id +
        '" data-url="' + cap.url +
        '" title="' + formatTimestamp(cap.created_at) + '">' +
        '<img src="' + thumbUrl + '" alt="Capture" loading="lazy" />' +
        '</div>';
    });
    this.$gallery.empty().append(html);

    this.$gallery.off("click.robotDashboardGallery").on("click.robotDashboardGallery", ".capture-card", function () {
      var url = $(this).data("url");
      if (url) self.showPreview(url);
    });

    return this;
  };

  DashboardBoard.prototype.showPreview = function (url) {
    var $overlay = $(
      '<div class="capture-preview-overlay">' +
      '<button class="capture-preview-close">&times;</button>' +
      '<img src="' + url + '" alt="Capture preview" />' +
      '</div>'
    );
    $("body").append($overlay);

    $overlay.on("click", function (e) {
      if (e.target === this || $(e.target).hasClass("capture-preview-close")) {
        $overlay.remove();
      }
    });

    $(document).one("keydown.robotDashboardPreview", function (e) {
      if (e.key === "Escape") {
        $overlay.remove();
        $(document).off("keydown.robotDashboardPreview");
      }
    });
  };

  /* ── Lifecycle ───────────────────────────────────── */

  DashboardBoard.prototype.destroy = function () {
    if (this.timerId) {
      window.clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.galleryTimerId) {
      window.clearInterval(this.galleryTimerId);
      this.galleryTimerId = null;
    }
    if (this.systemMetricsTimerId) {
      window.clearInterval(this.systemMetricsTimerId);
      this.systemMetricsTimerId = null;
    }
    if (this.socket && typeof this.socket.disconnect === "function") {
      this.socket.disconnect();
      this.socket = null;
    }
    this.$root.off(".robotDashboardBoard");
    this.$gallery.off(".robotDashboardGallery");
    this.$root.removeData("robotDashboardBoard");
    return this;
  };

  $.fn.robotDashboardBoard = function (methodOrOptions) {
    var args = Array.prototype.slice.call(arguments, 1);
    return this.each(function () {
      var instance = $.data(this, "robotDashboardBoard");
      if (!instance) {
        instance = new DashboardBoard(this, methodOrOptions);
        $.data(this, "robotDashboardBoard", instance);
        instance.init();
        return;
      }
      if (typeof methodOrOptions === "string" && typeof instance[methodOrOptions] === "function") {
        instance[methodOrOptions].apply(instance, args);
      }
    });
  };
})(jQuery);