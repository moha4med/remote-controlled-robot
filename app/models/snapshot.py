# app/models/snapshot.py
# Model for video stream snapshots — manual, event-based, or detection-triggered

from app.extensions import db
from datetime import datetime, timezone


class Snapshot(db.Model):
    __tablename__ = "snapshots"

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    filepath = db.Column(
        db.String(255),
        nullable=False
    )

    thumbnail_path = db.Column(
        db.String(255),
        nullable=True
    )

    file_size = db.Column(
        db.Integer,
        nullable=True
    )

    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)

    # Source: "manual" (user clicked button), "event" (abnormal sensor), "detection" (AI detection trigger)
    source = db.Column(
        db.String(20),
        nullable=False,
        default="manual"
    )

    # Event type description: "high_temperature", "low_battery", "object_detected", "manual", etc.
    event_type = db.Column(
        db.String(50),
        nullable=True
    )

    # Optional: store a JSON blob with context (sensor readings at time of capture, detection results, etc.)
    context_json = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self, base_url: str = ""):
        return {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "thumbnail_path": self.thumbnail_path,
            "file_size": self.file_size,
            "width": self.width,
            "height": self.height,
            "source": self.source,
            "event_type": self.event_type,
            "context_json": self.context_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": f"{base_url}/api/v1/snapshots/file/{self.filename}",
            "thumbnail_url": f"{base_url}/api/v1/snapshots/thumb/{self.filename}" if self.thumbnail_path else None,
        }