# app/models/latency_log.py
# Model for tracking API and WebSocket response latencies over time

from app.extensions import db
from datetime import datetime, timezone


class LatencyLog(db.Model):
    __tablename__ = "latency_log"

    id = db.Column(db.Integer, primary_key=True)
    # Type of latency measurement: "api", "websocket", "sensor_loop", "db_write"
    category = db.Column(db.String(30), nullable=False, default="api")
    # Endpoint or operation name (e.g., "/api/v1/status", "sensor_read")
    endpoint = db.Column(db.String(120), nullable=True)
    # Latency in milliseconds
    latency_ms = db.Column(db.Float, nullable=False)
    # HTTP status code (for API latencies)
    status_code = db.Column(db.Integer, nullable=True)
    # Optional extra context
    meta_json = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "endpoint": self.endpoint,
            "latency_ms": self.latency_ms,
            "status_code": self.status_code,
            "meta_json": self.meta_json,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }