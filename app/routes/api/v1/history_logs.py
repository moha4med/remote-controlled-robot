# app/routes/api/v1/history_logs.py
# Sensor history endpoint with time-range filtering.

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.models.sensor_log import SensorLog

history_logs_bp = Blueprint("history_logs", __name__, url_prefix="/api/v1/history")


@history_logs_bp.route("/", methods=["GET"])
@limiter.limit("30/minute")
def get_sensor_history():
    """Return sensor history with optional limit and time range.
    
    Query params:
        limit: max entries to return (default 120, max 500)
        hours: filter to last N hours (optional)
    """
    limit = request.args.get("limit", 120, type=int)
    limit = min(limit, 500)
    hours = request.args.get("hours", None, type=float)

    query = SensorLog.query.order_by(SensorLog.recorded_at.desc())

    if hours:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(SensorLog.recorded_at >= cutoff)

    logs = query.limit(limit).all()

    return jsonify([log.to_dict() for log in reversed(logs)])