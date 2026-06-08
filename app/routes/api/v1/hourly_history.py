# app/routes/api/v1/hourly_history.py
# Hourly aggregated sensor history for chart visualization.

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.models.sensor_log import SensorLog
from sqlalchemy import func, cast, DateTime
from datetime import datetime, timezone, timedelta

hourly_history_bp = Blueprint("hourly_history", __name__, url_prefix="/api/v1/history")


@hourly_history_bp.route("/hourly", methods=["GET"], strict_slashes=False)
@limiter.limit("30/minute")
def get_hourly_history():
    """Return hourly aggregated sensor data.

    Query params:
        hours: number of hours to look back (default 24, max 168)
    """
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)  # clamp 1-168 (1 week max)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Group by hour, compute averages
    # Use SQLite-compatible strftime for hour bucketing
    results = (
        SensorLog.query
        .filter(SensorLog.recorded_at >= cutoff)
        .with_entities(
            func.strftime("%Y-%m-%d %H:00:00", SensorLog.recorded_at).label("hour"),
            func.avg(SensorLog.temperature).label("avg_temp"),
            func.avg(SensorLog.humidity).label("avg_humidity"),
            func.count(SensorLog.id).label("count"),
        )
        .group_by(func.strftime("%Y-%m-%d %H:00:00", SensorLog.recorded_at))
        .order_by("hour")
        .all()
    )

    data = []
    for row in results:
        data.append({
            "hour": row.hour,
            "temperature": round(row.avg_temp, 1) if row.avg_temp is not None else None,
            "humidity": round(row.avg_humidity, 1) if row.avg_humidity is not None else None,
            "samples": row.count,
        })

    return jsonify(data)