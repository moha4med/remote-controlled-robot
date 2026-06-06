from app.extensions import db
from datetime import datetime, timezone


class Capture(db.Model):
    __tablename__ = "captures"

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": f"{base_url}/api/v1/captures/file/{self.filename}",
            "thumbnail_url": f"{base_url}/api/v1/captures/thumb/{self.filename}" if self.thumbnail_path else None,
        }
