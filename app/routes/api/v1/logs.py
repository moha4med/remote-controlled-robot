# app/routes/api/v1/logs.py
# API for retrieving sensor history and saving sensor logs

from flask import Blueprint, jsonify
from app.extensions import db
from app.models.sensor_log import SensorLog

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


@logs_bp.route("/sensors", methods=["GET"])
def get_sensor_history():
    """Return the last 120 sensor log entries (roughly 5 min at 2.5s intervals)."""
    logs = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .limit(120)
        .all()
    )
    return jsonify([log.to_dict() for log in reversed(logs)])