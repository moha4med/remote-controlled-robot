# app/routes/api/v1/settings.py
# API for user preferences, notification settings, and system configuration

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, limiter
from app.models.user import User
from app.models.setting import Setting

settings_bp = Blueprint("settings", __name__, url_prefix="/api/v1/settings")


# User Preferences

@settings_bp.route("/preferences", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def get_preferences():
    """Return the current user's preferences."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    prefs = Setting.get_user_preferences(user_id)
    return jsonify({
        "status": "success",
        "data": prefs,
    })


@settings_bp.route("/preferences", methods=["PUT"])
@jwt_required()
@limiter.limit("10/minute")
def update_preferences():
    """Update the current user's preferences."""
    user_id = int(get_jwt_identity())
    data = request.json or {}

    allowed_keys = {
        "theme", "language", "timezone",
        "mission_alerts", "sensor_alerts", "connection_alerts", "sound_enabled",
    }

    for key, value in data.items():
        if key in allowed_keys:
            Setting.set_user_preference(user_id, key, value)

    db.session.commit()

    prefs = Setting.get_user_preferences(user_id)
    return jsonify({
        "status": "success",
        "message": "Preferences updated",
        "data": prefs,
    })


# Notification Settings

@settings_bp.route("/notifications", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def get_notification_settings():
    """Return the current user's notification preferences."""
    user_id = int(get_jwt_identity())

    settings = {
        "mission_alerts": Setting.get_user_preference(user_id, "mission_alerts", True),
        "sensor_alerts": Setting.get_user_preference(user_id, "sensor_alerts", True),
        "connection_alerts": Setting.get_user_preference(user_id, "connection_alerts", True),
        "sound_enabled": Setting.get_user_preference(user_id, "sound_enabled", False),
    }

    return jsonify({"status": "success", "data": settings})


@settings_bp.route("/notifications", methods=["PUT"])
@jwt_required()
@limiter.limit("10/minute")
def update_notification_settings():
    """Update the current user's notification preferences."""
    user_id = int(get_jwt_identity())
    data = request.json or {}

    bool_keys = {"mission_alerts", "sensor_alerts", "connection_alerts", "sound_enabled"}
    for key in bool_keys:
        if key in data:
            Setting.set_user_preference(user_id, key, bool(data[key]))

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Notification settings updated",
    })


# System Configuration (admin only)

@settings_bp.route("/system", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def get_system_config():
    """Return system-wide configuration."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    if user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403

    configs = Setting.get_all_system()
    return jsonify({"status": "success", "data": configs})


@settings_bp.route("/system", methods=["PUT"])
@jwt_required()
@limiter.limit("10/minute")
def update_system_config():
    """Update system-wide configuration (admin only)."""
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)

    if user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403

    data = request.json or {}
    for key, value in data.items():
        Setting.set_system(key, value)

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "System configuration updated",
    })