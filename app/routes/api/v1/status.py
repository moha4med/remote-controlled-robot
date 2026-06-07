# app/routes/api/v1/status.py
# Combined status and events endpoints

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.services.robot_service import RobotService
from app.models.sensor_log import SensorLog
import time

status_bp = Blueprint("status", __name__, url_prefix="/api/v1")
robot = RobotService()


@status_bp.route("/status", methods=["GET"])
@limiter.limit("60/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def get_status():
    """Return a combined status snapshot."""
    latest = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .first()
    )

    payload = {
        "battery": 80,
        "signal": 92,
        "mode": "Manual",
        "temp": 47,
        "humidity": 60,
        "state": robot.state,
        "timestamp": time.time(),
    }

    if latest:
        payload["battery"] = round(latest.battery or 80)
        payload["signal"] = round(latest.signal_strength or 92)
        payload["temp"] = latest.temperature
        payload["humidity"] = latest.humidity
        payload["state"] = latest.robot_state or robot.state

    return jsonify(payload)


@status_bp.route("/events", methods=["POST"])
@limiter.limit("20/minute")
# @jwt_required_role("operator")  # uncomment to enable auth
def post_event():
    """Accept quick-action events from the dashboard."""
    action = request.form.get("action", "")
    print(f"[EVENT] Action received: {action}")

    action_map = {
        "start": "forward",
        "stop": "stop",
        "return": "left",
        "emergency": "stop",
    }
    cmd = action_map.get(action, "stop")
    if cmd == "forward":
        robot.forward()
    else:
        robot.stop()

    return jsonify({"status": "ok", "action": action, "robot_state": robot.state})