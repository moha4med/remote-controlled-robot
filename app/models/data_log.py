# app/models/data_log.py
# Model for system event logging — errors, warnings, info messages
# Provides an audit trail for debugging and monitoring

from app.extensions import db
from datetime import datetime, timezone


class DataLog(db.Model):
    __tablename__ = "data_log"

    id = db.Column(db.Integer, primary_key=True)
    # Severity level: "debug", "info", "warning", "error", "critical"
    level = db.Column(db.String(20), nullable=False, default="info")
    # Component that generated the log: "sensor_stream", "camera", "api", "system", etc.
    component = db.Column(db.String(50), nullable=True)
    # Short message
    message = db.Column(db.Text, nullable=False)
    # Optional stack trace or extra details
    details = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "component": self.component,
            "message": self.message,
            "details": self.details,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }