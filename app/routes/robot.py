#app/services/robot.py

from flask import Blueprint, jsonify
from app.services.robot_service import RobotService

robot_bp = Blueprint("robot", __name__)

robot = RobotService()

@robot_bp.route("move/<direction>", methods=["POST"])
def move(direction):
    if direction == "forward":
        robot.forward()
    elif direction == "backward":
        robot.backward()
    elif direction == "left":
        robot.left()
    elif direction == "right":
        robot.right()
    elif direction == "stop":
        robot.stop()

    return jsonify({
        "status": "ok",
        "direction": direction,
        "state": robot.state
    })
