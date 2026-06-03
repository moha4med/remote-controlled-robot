# app/services/robot_service.py

class RobotService:
    def __init__(self):
        self.state = "STOP"

    def forward(self):
        self.state = "FORWARD"
        print("[ROBOT] Moving forward")

    def backward(self):
        self.state = "BACKWARD"
        print("[ROBOT] Moving backward")

    def left(self):
        self.state = "LEFT"
        print("[ROBOT] Turning left")

    def right(self):
        self.state = "RIGHT"
        print("[ROBOT] Turning right")

    def stop(self):
        self.state = "STOP"
        print("[ROBOT] STOP")