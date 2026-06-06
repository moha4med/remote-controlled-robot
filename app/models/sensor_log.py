from app.extensions import db
from datetime import datetime, timezone


class SensorLog(db.Model):
    __tablename__ = "sensor_log"

    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    battery = db.Column(db.Float, nullable=True)
    signal_strength = db.Column(db.Float, nullable=True)
    robot_state = db.Column(db.String(20), nullable=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "battery": self.battery,
            "signal_strength": self.signal_strength,
            "robot_state": self.robot_state,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }