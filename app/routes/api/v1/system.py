# app/routes/api/v1/system.py
# System status endpoint

from flask import Blueprint, jsonify
from app.services.system_service import get_system_metrics
from app.extensions import limiter

system_bp = Blueprint("system", __name__, url_prefix="/api/v1/system")


@system_bp.route("/metrics", methods=["GET"])
@limiter.limit("30/minute")
def metrics():
    """Return current system metrics."""
    return jsonify(get_system_metrics())