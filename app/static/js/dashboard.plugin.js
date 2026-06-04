/**
 * Robot dashboard plugin.
 *
 * Responsibilities:
 * - Poll `/api/status` on a timer.
 * - Keep the dashboard metric cards in sync.
 * - Delegate quick-action button clicks.
 *
 * The plugin stores its state with `$.data()` and returns the jQuery collection
 * for chaining.
 */
(function ($) {
  "use strict";

  var DEFAULTS = {
    statusUrl: "/api/status",
    eventsUrl: "/api/events",
    pollIntervalMs: 2000,
  };

  function DashboardBoard(element, options) {
    this.$root = $(element);
    this.options = $.extend({}, DEFAULTS, options);
    this.$battery = this.$root.find("#batteryValue, #battery");
    this.$signal = this.$root.find("#signal");
    this.$mode = this.$root.find("#modeValue, #mode");
    this.$temp = this.$root.find("#temp");
    this.$timestamp = this.$root.find("#dashboardTimestamp");
    this.$actions = this.$root.find("[data-action]");
    this.timerId = null;
  }

  DashboardBoard.prototype.init = function () {
    var self = this;

    this.$root.attr("aria-busy", "true");
    this.$root.on("click.robotDashboardBoard", "[data-action]", function (event) {
      event.preventDefault();
      self.sendAction($(this).data("action"));
    });

    this.refresh();
    this.timerId = window.setInterval(function () {
      self.refresh();
    }, this.options.pollIntervalMs);
    this.$root.attr("aria-busy", "false");
    return this;
  };

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
    if (!data) {
      return this;
    }

    if (data.battery !== undefined) {
      this.$battery.text(data.battery);
    }
    if (data.signal !== undefined) {
      this.$signal.text(data.signal);
    }
    if (data.mode !== undefined) {
      this.$mode.text(data.mode);
    }
    if (data.temp !== undefined) {
      this.$temp.text(data.temp);
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

  DashboardBoard.prototype.destroy = function () {
    if (this.timerId) {
      window.clearInterval(this.timerId);
      this.timerId = null;
    }
    this.$root.off(".robotDashboardBoard");
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
