/**
 * Robot dashboard plugin.
 *
 * Responsibilities:
 * - Poll `/api/v1/status` every 2s for live telemetry.
 * - Animate numeric value transitions.
 * - Handle image capture via `/api/v1/captures/`.
 * - Display capture gallery with thumbnails and full-size preview.
 * - Delegate quick-action button clicks to `/api/v1/events`.
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    statusUrl: "/api/v1/status",
    eventsUrl: "/api/v1/events",
    capturesUrl: "/api/v1/captures/",
    pollIntervalMs: 2000,
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

  /* ── Plugin ──────────────────────────────────────── */

  function DashboardBoard(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);
    this.$battery = this.$root.find("#batteryValue");
    this.$signal = this.$root.find("#signal");
    this.$mode = this.$root.find("#modeValue");
    this.$temp = this.$root.find("#temp");
    this.$timestamp = this.$root.find("#dashboardTimestamp");
    this.$actions = this.$root.find("[data-action]");

    // Capture elements
    this.$btnCapture = this.$root.find("#btnCapture");
    this.$captureStatus = this.$root.find("#captureStatus");
    this.$captureCount = this.$root.find("#captureCount");
    this.$gallery = this.$root.find("#captureGallery");
    this.$galleryEmpty = this.$root.find("#galleryEmpty");
    this.$galleryCountText = this.$root.find("#galleryCountText");
    this.$cameraPreview = this.$root.find("#cameraPreviewImg");

    this.timerId = null;
    this.galleryTimerId = null;
    this.knownCaptureIds = {};
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

    this.$root.attr("aria-busy", "false");
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
    this.$timestamp.text(new Date().toLocaleTimeString());
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
      .html('<i data-feather="loader"></i> Capturing...')
      .removeClass("overlay-chip--success overlay-chip--danger")
      .addClass("overlay-chip--accent");

    $.ajax({
      url: this.options.capturesUrl,
      method: "POST",
      success: function (capture) {
        self.$captureStatus
          .html('<i data-feather="check-circle"></i> Captured!')
          .removeClass("overlay-chip--accent overlay-chip--danger")
          .addClass("overlay-chip--success");

        self.loadGallery();

        if (self.$cameraPreview.length && capture.thumbnail_url) {
          self.$cameraPreview.attr("src", capture.thumbnail_url + "?t=" + Date.now());
        }

        if (window.feather) {
          feather.replace({ width: 18, height: 18 });
        }
      },
      error: function () {
        self.$captureStatus
          .html('<i data-feather="alert-triangle"></i> Failed')
          .removeClass("overlay-chip--accent overlay-chip--success")
          .addClass("overlay-chip--danger");
      },
      complete: function () {
        self.$btnCapture.prop("disabled", false);
        window.setTimeout(function () {
          self.$captureStatus
            .html('<i data-feather="check-circle"></i> Ready')
            .removeClass("overlay-chip--accent overlay-chip--danger")
            .addClass("overlay-chip--success");
          if (window.feather) {
            feather.replace({ width: 18, height: 18 });
          }
        }, 3000);
      },
    });
  };

  /* ── Gallery ──────────────────────────────────────── */

  DashboardBoard.prototype.loadGallery = function () {
    var self = this;
    $.getJSON(this.options.capturesUrl)
      .done(function (captures) {
        self.renderGallery(captures);
      });
  };

  DashboardBoard.prototype.renderGallery = function (captures) {
    if (!captures || !captures.length) {
      this.$gallery.empty().append(this.$galleryEmpty);
      this.$captureCount.text("0");
      this.$galleryCountText.text("0");
      return this;
    }

    this.$captureCount.text(captures.length);
    this.$galleryCountText.text(captures.length);

    var hadItems = Object.keys(this.knownCaptureIds).length > 0;
    var prevFirstId = Object.keys(this.knownCaptureIds)[0];
    var hasNew = false;

    var html = "";
    var self = this;
    $.each(captures, function (_, cap) {
      self.knownCaptureIds[cap.id] = true;
      if (!hadItems || (prevFirstId && cap.id > parseInt(prevFirstId))) {
        hasNew = true;
      }
      var thumbUrl = cap.thumbnail_url || cap.url;
      html +=
        '<div class="capture-card" data-id="' + cap.id +
        '" data-url="' + cap.url +
        '" title="' + formatTimestamp(cap.created_at) + '">' +
        '<img src="' + thumbUrl + '" alt="Capture" loading="lazy" />' +
        '<span class="capture-card__time">' + formatTimestamp(cap.created_at) + '</span>' +
        '</div>';
    });
    this.$gallery.empty().append(html);

    this.$gallery.off("click.robotDashboardGallery").on("click.robotDashboardGallery", ".capture-card", function () {
      var url = $(this).data("url");
      if (url) self.showPreview(url);
    });

    if (hasNew && this.$gallery.length) {
      this.$gallery.scrollTop(0);
    }

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