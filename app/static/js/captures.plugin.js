/**
 * Captures gallery plugin.
 *
 * Responsibilities:
 * - Load and display capture gallery from `/api/v1/captures/`
 * - Trigger new captures via POST `/api/v1/captures/`
 * - Full-size preview overlay with keyboard/click dismiss
 * - Auto-poll for new captures
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    capturesUrl: "/api/v1/captures/",
    pollIntervalMs: 5000,
  };

  function CapturesGallery(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);
    this.$gallery = this.$root.find("#captureGallery");
    this.$empty = this.$root.find("#galleryEmpty");
    this.$count = this.$root.find("#captureCount");
    this.$btnNew = this.$root.find("#btnNewCapture");
    this.pollTimer = null;
    this.knownIds = {};
  }

  CapturesGallery.prototype.init = function () {
    var self = this;

    // New capture button
    if (this.$btnNew.length) {
      this.$btnNew.on("click.captures", function () {
        self.triggerCapture();
      });
    }

    // Gallery click for preview
    this.$gallery.on("click.captures", ".capture-card", function () {
      var url = $(this).data("url");
      if (url) self.showPreview(url);
    });

    // Load and poll
    this.loadGallery();
    this.pollTimer = window.setInterval(function () {
      self.loadGallery();
    }, this.options.pollIntervalMs);

    return this;
  };

  CapturesGallery.prototype.loadGallery = function () {
    var self = this;
    $.getJSON(this.options.capturesUrl)
      .done(function (data) {
        var items = data.items || data;
        if (Array.isArray(items)) {
          self.renderGallery(items);
        }
      });
  };

  CapturesGallery.prototype.renderGallery = function (captures) {
    if (!captures || !captures.length) {
      this.$gallery.empty().append(
        '<div class="text-center text-muted py-5 w-100">' +
        '<i class="bi bi-camera" style="font-size:32px;opacity:.4"></i>' +
        '<p class="mt-2 mb-0">No captures yet. Click <strong>New Capture</strong> to take a photo.</p>' +
        '</div>'
      );
      this.$count.text("0");
      return this;
    }

    this.$count.text(captures.length);

    var html = "";
    var self = this;
    $.each(captures, function (_, cap) {
      self.knownIds[cap.id] = true;
      var thumbUrl = cap.thumbnail_url || cap.url;
      var time = cap.created_at ? new Date(cap.created_at).toLocaleTimeString() : "";
      html +=
        '<div class="capture-card" data-id="' + cap.id +
        '" data-url="' + cap.url +
        '" title="' + time + '">' +
        '<img src="' + thumbUrl + '" alt="Capture" loading="lazy" />' +
        '<span class="capture-card__time">' + time + '</span>' +
        '</div>';
    });
    this.$gallery.empty().append(html);

    return this;
  };

  CapturesGallery.prototype.triggerCapture = function () {
    var self = this;
    this.$btnNew.prop("disabled", true).html('<i class="bi bi-arrow-repeat spin me-1"></i> Capturing...');

    $.ajax({
      url: this.options.capturesUrl,
      method: "POST",
      success: function () {
        self.loadGallery();
      },
      error: function () {
        alert("Capture failed. Please try again.");
      },
      complete: function () {
        self.$btnNew.prop("disabled", false).html('<i class="bi bi-camera-fill me-1"></i> New Capture');
      },
    });
  };

  CapturesGallery.prototype.showPreview = function (url) {
    var self = this;
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

    $(document).one("keydown.capturesPreview", function (e) {
      if (e.key === "Escape") {
        $overlay.remove();
        $(document).off("keydown.capturesPreview");
      }
    });
  };

  CapturesGallery.prototype.destroy = function () {
    if (this.pollTimer) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.$gallery.off(".captures");
    this.$btnNew.off(".captures");
    this.$root.removeData("capturesGallery");
  };

  $.fn.capturesGallery = function (methodOrOptions) {
    var args = Array.prototype.slice.call(arguments, 1);
    return this.each(function () {
      var instance = $.data(this, "capturesGallery");
      if (!instance) {
        instance = new CapturesGallery(this, methodOrOptions);
        $.data(this, "capturesGallery", instance);
        instance.init();
        return;
      }
      if (typeof methodOrOptions === "string" && typeof instance[methodOrOptions] === "function") {
        instance[methodOrOptions].apply(instance, args);
      }
    });
  };
})(jQuery);