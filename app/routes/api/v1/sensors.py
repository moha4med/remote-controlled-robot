# app/routes/api/v1/sensors.py
# All sensor-related endpoints: current readings, history, hourly aggregation, and statistics.

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import limiter
from app.models.sensor_log import SensorLog

sensors_bp = Blueprint("sensors_api", __name__, url_prefix="/api/v1/sensors")


@sensors_bp.route("/", methods=["GET"])
@limiter.limit("60/minute")
def environment():
    """Return the latest sensor reading from the database."""
    latest = (SensorLog.query.order_by(SensorLog.recorded_at.desc()).first())
    if not latest:
        return jsonify({
            "status": "error",
            "data": {
                "temperature": None,
                "humidity": None
            },
            "message": "No sensor data available"
        }), 404
    return jsonify({"status": "success", "data": latest.to_dict()})


@sensors_bp.route("/history", methods=["GET"])
@limiter.limit("30/minute")
def history():
    """Return raw sensor readings within a time range.

    Query params:
      hours: number of hours to look back (default: 24, max: 168)
      limit: max entries to return (default: 500, max: 1000)
    """
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)
    limit = request.args.get("limit", 500, type=int)
    limit = min(limit, 1000)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    readings = (SensorLog.query.filter(
        SensorLog.recorded_at >= since).order_by(
            SensorLog.recorded_at.asc()).limit(limit).all())

    return jsonify({
        "status": "success",
        "data": {
            "hours": hours,
            "count": len(readings),
            "items": [r.to_dict() for r in readings],
        }
    })


@sensors_bp.route("/history/hourly", methods=["GET"])
@limiter.limit("30/minute")
def hourly_history():
    """Return hourly aggregated sensor data for chart visualization.

    Query params:
      hours: number of hours to look back (default: 24, max: 168)
    """
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    results = (SensorLog.query.filter(
        SensorLog.recorded_at >= cutoff).with_entities(
            func.strftime("%Y-%m-%d %H:00:00",
                          SensorLog.recorded_at).label("hour"),
            func.avg(SensorLog.temperature).label("avg_temp"),
            func.avg(SensorLog.humidity).label("avg_humidity"),
            func.count(SensorLog.id).label("count"),
        ).group_by(
            func.strftime("%Y-%m-%d %H:00:00",
                          SensorLog.recorded_at)).order_by("hour").all())

    data = []
    for row in results:
        data.append({
            "hour":
            row.hour,
            "temperature":
            round(row.avg_temp, 1) if row.avg_temp is not None else None,
            "humidity":
            round(row.avg_humidity, 1)
            if row.avg_humidity is not None else None,
            "samples":
            row.count,
        })

    return jsonify({"status": "success", "data": data})


@sensors_bp.route("/stats", methods=["GET"])
@limiter.limit("30/minute")
def stats():
    """Return aggregated sensor statistics for a time range.

    Query params:
      hours: number of hours to look back (default: 24, max: 168)
    """
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = (SensorLog.query.filter(
        SensorLog.recorded_at >= since).with_entities(
            func.count(SensorLog.id).label("count"),
            func.avg(SensorLog.temperature).label("avg_temp"),
            func.min(SensorLog.temperature).label("min_temp"),
            func.max(SensorLog.temperature).label("max_temp"),
            func.avg(SensorLog.humidity).label("avg_humidity"),
            func.min(SensorLog.humidity).label("min_humidity"),
            func.max(SensorLog.humidity).label("max_humidity"),
            func.avg(SensorLog.battery).label("avg_battery"),
            func.avg(SensorLog.signal_strength).label("avg_signal"),
        ).first())

    if not result or result.count == 0:
        return jsonify({
            "status": "error",
            "data": {
                "hours": hours,
                "count": 0,
                "message": "No sensor data available for this period.",
            }
        }), 404

    return jsonify({
        "status": "success",
        "data": {
            "hours": hours,
            "count": result.count,
            "temperature": {
                "avg": round(result.avg_temp, 1) if result.avg_temp else None,
                "min": round(result.min_temp, 1) if result.min_temp else None,
                "max": round(result.max_temp, 1) if result.max_temp else None,
            },
            "humidity": {
                "avg":
                round(result.avg_humidity, 1) if result.avg_humidity else None,
                "min":
                round(result.min_humidity, 1) if result.min_humidity else None,
                "max":
                round(result.max_humidity, 1) if result.max_humidity else None,
            },
            "battery": {
                "avg":
                round(result.avg_battery, 1) if result.avg_battery else None,
            },
            "signal": {
                "avg":
                round(result.avg_signal, 1) if result.avg_signal else None,
            },
        }
    })