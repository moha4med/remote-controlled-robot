# app/routes/api/v1/latency.py
# Latency monitoring endpoints — stats, history, and category breakdown

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.services.latency_monitor import monitor

latency_bp = Blueprint("latency", __name__, url_prefix="/api/v1/latency")


@latency_bp.route("/", methods=["GET"])
@limiter.limit("60/minute")
def get_latency_stats():
    """Return current latency statistics."""
    window = request.args.get("window", 60, type=int)
    window = min(max(window, 10), 600)
    stats = monitor.get_current_stats(window_seconds=window)
    
    return jsonify({"status": "success", "data": stats})


@latency_bp.route("/history", methods=["GET"])
@limiter.limit("30/minute")
def get_latency_history():
    """Return time-bucketed latency history for charting."""
    window = request.args.get("window", 300, type=int)
    window = min(max(window, 30), 3600)
    bucket_ms = request.args.get("bucket_ms", 5000, type=int)
    bucket_ms = min(max(bucket_ms, 1000), 60000)
    history = monitor.get_history(window_seconds=window, bucket_ms=bucket_ms)
    
    return jsonify({"status": "success", "data": history})


@latency_bp.route("/categories", methods=["GET"])
@limiter.limit("30/minute")
def get_latency_categories():
    """Return latency stats broken down by category."""
    window = request.args.get("window", 60, type=int)
    window = min(max(window, 10), 600)
    breakdown = monitor.get_category_breakdown(window_seconds=window)
    
    return jsonify({"status": "success", "data": breakdown})