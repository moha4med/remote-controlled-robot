# app/middleware/latency.py
# Flask before/after request middleware for automatic API latency tracking

import time
from flask import request, g
from app.services.latency_monitor import monitor


def register_latency_middleware(app):
    """Attach before/after request hooks to measure API latency."""

    @app.before_request
    def _start_timer():
        g._request_start_time = time.time()

    @app.after_request
    def _record_latency(response):
        if hasattr(g, '_request_start_time'):
            elapsed_ms = (time.time() - g._request_start_time) * 1000
            # Skip static files and the latency endpoint itself
            if not request.path.startswith('/static') and not request.path.startswith('/api/v1/latency'):
                monitor.record(
                    latency_ms=elapsed_ms,
                    category="api",
                    endpoint=request.path,
                    status_code=response.status_code,
                )
        return response