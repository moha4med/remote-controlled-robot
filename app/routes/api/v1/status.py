# app/routes/api/v1/status.py
# Combined status and events endpoints

import subprocess
import re
import time

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.services.robot_service import RobotService
from app.models.sensor_log import SensorLog

status_bp = Blueprint("status", __name__, url_prefix="/api/v1")
robot = RobotService()


def _get_wifi_signal_strength():
    """Try to read WiFi signal strength from the system.

    Returns signal quality as a percentage (0-100), or None if unavailable.
    Works on Linux (Raspberry Pi) via iwconfig or /proc/net/wireless.
    """
    try:
        # Try /proc/net/wireless first (most reliable on Linux)
        with open("/proc/net/wireless", "r") as f:
            for line in f:
                if "wlan" in line:
                    # Format: iface: status link_level noise
                    # link_level is in dBm, typically -30 (great) to -90 (poor)
                    parts = line.split()
                    if len(parts) >= 4:
                        # parts[3] is the signal level like -45.
                        raw = parts[3].rstrip(".")
                        dbm = int(raw)
                        # Convert dBm to percentage: -30=100%, -90=0%
                        pct = max(0, min(100, 2 * (dbm + 90)))
                        return round(pct)
    except (FileNotFoundError, ValueError, IndexError, PermissionError):
        pass

    try:
        # Fallback: try iwconfig
        result = subprocess.run(["iwconfig"],
                                capture_output=True,
                                text=True,
                                timeout=5)
        # Look for "Signal level=-45 dBm" or "Quality=70/70"
        m = re.search(r"Signal level[=:]\s*(-?\d+)\s*dBm", result.stdout)
        if m:
            dbm = int(m.group(1))
            pct = max(0, min(100, 2 * (dbm + 90)))
            return round(pct)
        m = re.search(r"Quality[=:](\d+)/(\d+)", result.stdout)
        if m:
            num, den = int(m.group(1)), int(m.group(2))
            return round(num / den * 100) if den else None
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass

    return None


@status_bp.route("/status", methods=["GET"])
@limiter.limit("60/minute")
# @jwt_required_role("operator")
def get_status():
    """Return a combined status snapshot."""
    latest = (SensorLog.query.order_by(SensorLog.recorded_at.desc()).first())

    # Get real WiFi signal strength
    wifi_signal = _get_wifi_signal_strength()

    payload = {
        "battery": 100,
        "signal": wifi_signal if wifi_signal is not None else 95,
        "mode": "Manual",
        "temp": 47,
        "humidity": 60,
        "state": robot.state,
        "timestamp": time.time(),
    }

    if latest:
        # Robot is USB-powered — no real battery; keep at 100%
        # unless sensor log explicitly reports a value
        payload["battery"] = round(
            latest.battery) if latest.battery is not None else 100
        # Use sensor log signal_strength if available, else use WiFi reading
        if latest.signal_strength is not None:
            payload["signal"] = round(latest.signal_strength)
        # else keep the wifi_signal value already set
        payload["temp"] = latest.temperature
        payload["humidity"] = latest.humidity
        payload["state"] = latest.robot_state or robot.state

    return jsonify({"status": "success", "data": payload})


@status_bp.route("/events", methods=["POST"])
@limiter.limit("20/minute")
# @jwt_required_role("operator")
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

    return jsonify({
        "status": "success",
        "data": {
            "action": action,
            "robot_state": robot.state
        }
    })
