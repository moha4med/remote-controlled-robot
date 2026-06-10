# app/services/latency_monitor.py
# Centralized latency tracking service
# Collects, stores, and provides statistics on API and WebSocket latencies

import time
import json
import threading
from collections import deque
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.latency_log import LatencyLog
from app.models.data_log import DataLog


class LatencyMonitor:
    """Tracks latency metrics in-memory and persists to database."""

    def __init__(self, max_memory_samples=500, persist_interval=30):
        self._lock = threading.Lock()
        self._samples = deque(maxlen=max_memory_samples)
        self._persist_interval = persist_interval
        self._last_persist = time.time()
        self._pending_persist = []

    def record(self, latency_ms, category="api", endpoint=None, status_code=None, meta=None):
        """Record a latency measurement."""
        entry = {
            "category": category,
            "endpoint": endpoint,
            "latency_ms": round(latency_ms, 2),
            "status_code": status_code,
            "meta": meta,
            "timestamp": datetime.now(timezone.utc),
        }
        with self._lock:
            self._samples.append(entry)
            self._pending_persist.append(entry)

        # Periodically flush to DB
        now = time.time()
        if now - self._last_persist >= self._persist_interval:
            self._flush_to_db()

    def _flush_to_db(self):
        """Write pending latency samples to the database."""
        with self._lock:
            to_write = list(self._pending_persist)
            self._pending_persist.clear()
            self._last_persist = time.time()

        for entry in to_write:
            try:
                log = LatencyLog(
                    category=entry["category"],
                    endpoint=entry.get("endpoint"),
                    latency_ms=entry["latency_ms"],
                    status_code=entry.get("status_code"),
                    meta_json=json.dumps(entry["meta"]) if entry.get("meta") else None,
                )
                db.session.add(log)
            except Exception as e:
                pass

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def get_current_stats(self, window_seconds=60):
        """Get latency statistics for the recent window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        with self._lock:
            recent = [s for s in self._samples if s["timestamp"] >= cutoff]

        if not recent:
            return {
                "count": 0,
                "avg_ms": None,
                "min_ms": None,
                "max_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
                "current_ms": None,
            }

        latencies = sorted([s["latency_ms"] for s in recent])
        n = len(latencies)

        return {
            "count": n,
            "avg_ms": round(sum(latencies) / n, 2),
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "p50_ms": round(latencies[int(n * 0.5)], 2),
            "p95_ms": round(latencies[int(n * 0.95)] if n > 1 else latencies[0], 2),
            "p99_ms": round(latencies[int(n * 0.99)] if n > 1 else latencies[0], 2),
            "current_ms": round(latencies[-1], 2),
        }

    def get_history(self, window_seconds=300, bucket_ms=5000):
        """Get time-bucketed latency history for charting."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        with self._lock:
            recent = [s for s in self._samples if s["timestamp"] >= cutoff]

        if not recent:
            return []

        bucket_count = max(1, window_seconds * 1000 // bucket_ms)
        buckets = [[] for _ in range(bucket_count)]
        now = datetime.now(timezone.utc)

        for s in recent:
            age_ms = (now - s["timestamp"]).total_seconds() * 1000
            idx = bucket_count - 1 - int(age_ms / bucket_ms)
            if 0 <= idx < bucket_count:
                buckets[idx].append(s["latency_ms"])

        result = []
        for i, bucket in enumerate(buckets):
            if bucket:
                result.append({
                    "timestamp": (now - timedelta(milliseconds=(bucket_count - 1 - i) * bucket_ms)).isoformat(),
                    "avg_ms": round(sum(bucket) / len(bucket), 2),
                    "max_ms": round(max(bucket), 2),
                    "count": len(bucket),
                })

        return result

    def get_category_breakdown(self, window_seconds=60):
        """Get latency stats broken down by category."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        with self._lock:
            recent = [s for s in self._samples if s["timestamp"] >= cutoff]

        categories = {}
        for s in recent:
            cat = s.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(s["latency_ms"])

        result = {}
        for cat, latencies in categories.items():
            latencies.sort()
            n = len(latencies)
            result[cat] = {
                "count": n,
                "avg_ms": round(sum(latencies) / n, 2),
                "p95_ms": round(latencies[int(n * 0.95)] if n > 1 else latencies[0], 2),
            }

        return result


# Singleton instance
monitor = LatencyMonitor()