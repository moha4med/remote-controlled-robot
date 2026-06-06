# app/routes/api/v1/robot.py
# Robot movement control

from flask import Blueprint, jsonify, request
from app.extensions import limiter
from app.services.robot_service import RobotService

robot_bp = Blueprint("robot", __name__, url_prefix="/api/v1/robot")
robot = RobotService()


@robot_bp.route("/move", methods=["POST"])
@limiter.limit("20/minute")
def move():
    direction = (
        request.form.get("direction", "").lower()
        or (request.json or {}).get("direction", "").lower()
    )

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