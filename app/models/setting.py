# app/models/setting.py
# Key-value store for user preferences and system configuration

from app.extensions import db
from datetime import datetime, timezone
import json


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text, nullable=True)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "key", name="uq_user_setting"),
    )

    @staticmethod
    def _serialize(value) -> str:
        """Serialize a Python value to a JSON string for storage."""
        return json.dumps(value)

    @staticmethod
    def _deserialize(raw: str):
        """Deserialize a stored JSON string back to a Python value."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    @classmethod
    def get_user_preference(cls, user_id: int, key: str, default=None):
        """Get a single user preference."""
        row = cls.query.filter_by(user_id=user_id, key=key, is_system=False).first()
        if row is None:
            return default
        return cls._deserialize(row.value)

    @classmethod
    def set_user_preference(cls, user_id: int, key: str, value):
        """Set a single user preference (upsert)."""
        row = cls.query.filter_by(user_id=user_id, key=key, is_system=False).first()
        if row is None:
            row = cls(user_id=user_id, key=key, is_system=False)
            db.session.add(row)
        row.value = cls._serialize(value)

    @classmethod
    def get_user_preferences(cls, user_id: int) -> dict:
        """Get all preferences for a user as a dict."""
        rows = cls.query.filter_by(user_id=user_id, is_system=False).all()
        return {row.key: cls._deserialize(row.value) for row in rows}

    @classmethod
    def get_system(cls, key: str, default=None):
        """Get a system-wide configuration value."""
        row = cls.query.filter_by(user_id=None, key=key, is_system=True).first()
        if row is None:
            return default
        return cls._deserialize(row.value)

    @classmethod
    def set_system(cls, key: str, value):
        """Set a system-wide configuration value (upsert)."""
        row = cls.query.filter_by(user_id=None, key=key, is_system=True).first()
        if row is None:
            row = cls(user_id=None, key=key, is_system=True)
            db.session.add(row)
        row.value = cls._serialize(value)

    @classmethod
    def get_all_system(cls) -> dict:
        """Get all system configuration as a dict."""
        rows = cls.query.filter_by(user_id=None, is_system=True).all()
        return {row.key: cls._deserialize(row.value) for row in rows}