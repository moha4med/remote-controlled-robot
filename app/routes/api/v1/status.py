# app/routes/api/v1/status.py
# Combined status, events, and move endpoints for jQuery frontend

from flask import Blueprint, jsonify, request
from app.services.robot_service import RobotService
from app.models.sensor_log import SensorLog
from datetime import datetime, timezone
import time

status_bp = Blueprint("status", __name__, url_prefix="/api/v1")
robot = RobotService()


@status_bp.route("/status", methods=["GET"])
def get_status():
    """Return a combined status snapshot from the latest DB record + robot state."""
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
def post_event():
    """Accept quick-action events from the dashboard."""
    action = request.form.get("action", "")
    print(f"[EVENT] Action received: {action}")

    # Map actions to robot commands
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


@status_bp.route("/move", methods=["POST"])
def move_robot():
    """Move endpoint used by control.plugin.js (form-encoded POST)."""
    direction = request.form.get("direction", "").lower()

    if direction == "forward":
        robot.forward()
    elif direction == "backward":
        robot.backward()
    elif direction == "left":
        robot.left()
    elif direction == "right":
        robot.right()
    else:
        robot.stop()

    return jsonify({
        "status": "ok",
        "direction": direction,
        "state": robot.state,
    })