# app/services/sensor_stream.py
# Sensor data acquisition, persistence, and Socket.IO broadcasting.

import time
from app.extensions import socketio, db
from app.sensors.usb_temp_humidity import USBTempHumiditySensor
from app.models.sensor_log import SensorLog
from app.services.robot_service import RobotService
from app.services.system_service import get_system_metrics


class SensorStreamManager:
    """Central manager for sensor data acquisition, persistence, and broadcast."""

    def __init__(self):
        self._sensor = None
        self._init_sensor()
        self.robot = RobotService()
        self._system_interval = 5.0
        self._last_system_emit = 0

    def _init_sensor(self):
        try:
            self._sensor = USBTempHumiditySensor("COM5", baudrate=9600)
        except Exception:
            self._sensor = None

    @property
    def sensor(self):
        if self._sensor is None:
            self._init_sensor()
        return self._sensor

    def read_sensors(self):
        """Read physical sensors, fall back to simulated values."""
        import random

        temp = None
        humidity = None
        s = self.sensor
        if s is not None:
            try:
                data = s.read()
                if data:
                    temp = data.get("temperature")
                    humidity = data.get("humidity")
            except Exception:
                pass

        # Fallback simulated values if no hardware
        if temp is None:
            temp = round(22 + random.uniform(-3, 3), 1)
        if humidity is None:
            humidity = round(55 + random.uniform(-10, 10), 1)

        battery = round(100)
        signal = round(90 + random.uniform(-8, 2), 1)

        return {
            "temperature": temp,
            "humidity": humidity,
            "battery": battery,
            "signal": signal,
            "robot_state": self.robot.state,
            "timestamp": time.time(),
        }

    def persist(self, data):
        """Save sensor snapshot to database."""
        try:
            log = SensorLog(
                temperature=data.get("temperature"),
                humidity=data.get("humidity"),
                battery=data.get("battery"),
                signal_strength=data.get("signal"),
                robot_state=data.get("robot_state"),
            )
            
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def read_and_broadcast(self):
        """Read sensors, persist, emit via SocketIO."""
        data = self.read_sensors()
        self.persist(data)
        socketio.emit("sensor:update", {
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "battery": data["battery"],
            "signal": data["signal"],
            "robot_state": data["robot_state"],
            "timestamp": data["timestamp"],
        })

    def broadcast_system_metrics(self):
        """Read system metrics and emit via SocketIO."""
        metrics = get_system_metrics()
        socketio.emit("system:update", metrics)


manager = SensorStreamManager()


def sensor_loop(app):
    """Background loop: read sensors, persist, emit every 2.5s.
    System metrics emitted every 5s.
    
    Must be called with the Flask app so DB operations work in the 
    background thread context.
    """
    with app.app_context():
        while True:
            try:
                manager.read_and_broadcast()
                now = time.time()
                if now - manager._last_system_emit >= manager._system_interval:
                    manager.broadcast_system_metrics()
                    manager._last_system_emit = now
            except Exception as e:
                socketio.emit("sensor:error", {"error": str(e)})
            socketio.sleep(2.5)
