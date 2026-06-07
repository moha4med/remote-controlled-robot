# app/routes/api/v1/logs.py
# API for retrieving sensor history

from flask import Blueprint, jsonify
from app.extensions import db, limiter
from app.models.sensor_log import SensorLog

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


@logs_bp.route("/sensors", methods=["GET"])
@limiter.limit("30/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def get_sensor_history():
    """Return the last 120 sensor log entries."""
    logs = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .limit(120)
        .all()
    )
    return jsonify([log.to_dict() for log in reversed(logs)])