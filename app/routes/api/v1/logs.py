# app/routes/api/v1/logs.py
# System data log endpoints — query recent events, stats, and trigger pruning

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.services.data_logger import data_logger

logs_bp = Blueprint("logs", __name__, url_prefix="/api/v1/logs")


@logs_bp.route("/", methods=["GET"])
@limiter.limit("30/minute")
def get_logs():
    """Return recent system log entries with optional filtering."""
    level = request.args.get("level", None)
    component = request.args.get("component", None)
    limit = request.args.get("limit", 50, type=int)
    limit = min(max(limit, 1), 200)
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)

    entries = data_logger.get_recent(
        level=level, component=component, limit=limit, hours=hours
    )
    return jsonify({
        "status": "success",
        "data": {
            "count": len(entries),
            "items": entries,
        }
    })


@logs_bp.route("/stats", methods=["GET"])
@limiter.limit("30/minute")
def get_log_stats():
    """Return log entry counts by level for the given time window."""
    hours = request.args.get("hours", 24, type=int)
    hours = min(max(hours, 1), 168)
    stats = data_logger.get_stats(hours=hours)
    return jsonify(stats)


@logs_bp.route("/prune", methods=["POST"])
@limiter.limit("5/minute")
def prune_logs():
    """Remove log entries older than the specified age."""
    max_age = request.args.get("max_age_hours", 168, type=int)
    max_age = min(max(max_age, 1), 720)
    deleted = data_logger.prune(max_age_hours=max_age)
    return jsonify({
        "status": "success",
        "data": {
            "status": "ok",
            "deleted": deleted,
            "max_age_hours": max_age,
        }
    })