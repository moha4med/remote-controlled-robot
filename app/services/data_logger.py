# app/services/data_logger.py
# Robust data logging service with buffering, retry, and system event tracking

import time
import json
import threading
from collections import deque
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.data_log import DataLog


class DataLogger:
    """Buffered system event logger with automatic retry and pruning."""

    def __init__(self, buffer_size=200, flush_interval=15, max_retries=3):
        self._lock = threading.Lock()
        self._buffer = deque(maxlen=buffer_size)
        self._flush_interval = flush_interval
        self._max_retries = max_retries
        self._last_flush = time.time()
        self._dropped_count = 0

    def log(self, level, message, component=None, details=None):
        """Add a log entry to the buffer."""
        entry = {
            "level": level,
            "component": component,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc),
        }
        with self._lock:
            if len(self._buffer) >= self._buffer.maxlen:
                self._dropped_count += 1
            self._buffer.append(entry)

        # Auto-flush on error/critical or periodic interval
        now = time.time()
        if level in ("error", "critical") or now - self._last_flush >= self._flush_interval:
            self.flush()

    def debug(self, message, component=None, details=None):
        self.log("debug", message, component, details)

    def info(self, message, component=None, details=None):
        self.log("info", message, component, details)

    def warning(self, message, component=None, details=None):
        self.log("warning", message, component, details)

    def error(self, message, component=None, details=None):
        self.log("error", message, component, details)

    def critical(self, message, component=None, details=None):
        self.log("critical", message, component, details)

    def flush(self):
        """Flush buffered logs to the database with retry."""
        with self._lock:
            to_write = list(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()

        if not to_write:
            return

        for attempt in range(self._max_retries):
            try:
                for entry in to_write:
                    log = DataLog(
                        level=entry["level"],
                        component=entry.get("component"),
                        message=entry["message"],
                        details=entry.get("details"),
                    )
                    db.session.add(log)
                db.session.commit()
                return
            except Exception:
                db.session.rollback()
                if attempt < self._max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))

        # All retries failed — re-buffer what we can
        with self._lock:
            for entry in to_write:
                if len(self._buffer) < self._buffer.maxlen:
                    self._buffer.appendleft(entry)

    def get_recent(self, level=None, component=None, limit=50, hours=24):
        """Query recent log entries from the database."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = DataLog.query.filter(DataLog.recorded_at >= cutoff)

        if level:
            query = query.filter(DataLog.level == level)
        if component:
            query = query.filter(DataLog.component == component)

        entries = (
            query.order_by(DataLog.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [e.to_dict() for e in entries]

    def get_stats(self, hours=24):
        """Get log entry counts by level."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        from sqlalchemy import func

        results = (
            DataLog.query
            .filter(DataLog.recorded_at >= cutoff)
            .with_entities(DataLog.level, func.count(DataLog.id))
            .group_by(DataLog.level)
            .all()
        )

        stats = {row[0]: row[1] for row in results}
        stats["total"] = sum(stats.values())
        stats["dropped_buffer"] = self._dropped_count
        return stats

    def prune(self, max_age_hours=168):
        """Remove log entries older than max_age_hours (default: 7 days)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        try:
            deleted = DataLog.query.filter(DataLog.recorded_at < cutoff).delete()
            db.session.commit()
            return deleted
        except Exception:
            db.session.rollback()
            return 0


# Singleton instance
data_logger = DataLogger()