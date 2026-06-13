# app/models/crop_profile.py

from app.extensions import db
from datetime import datetime, timezone


class CropProfile(db.Model):
    __tablename__ = "crop_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    optimal_temp_min = db.Column(db.Float, nullable=False)
    optimal_temp_max = db.Column(db.Float, nullable=False)
    optimal_humidity_min = db.Column(db.Float, nullable=False)
    optimal_humidity_max = db.Column(db.Float, nullable=False)
    frost_sensitive = db.Column(db.Boolean, nullable=False, default=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "optimal_temp_min": self.optimal_temp_min,
            "optimal_temp_max": self.optimal_temp_max,
            "optimal_humidity_min": self.optimal_humidity_min,
            "optimal_humidity_max": self.optimal_humidity_max,
            "frost_sensitive": self.frost_sensitive,
            "description": self.description,
            "is_active": self.is_active,
        }
