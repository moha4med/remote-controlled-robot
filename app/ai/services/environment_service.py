# app/ai/services/environment_service.py
# Service layer: fetches latest sensor data and runs the analysis engine.

from datetime import datetime, timezone

from app.ai.environmental.analyzer import analyze
from app.models.sensor_log import SensorLog


def get_environment_analysis():
    """Fetch the latest sensor reading from DB and return full analysis.

    Returns a dict with:
      - temperature, humidity: current values
      - status: Optimal / Warning / Critical
      - risk_level: Low / Medium / High
      - score: 0-100
      - temperature_trend: Stable / Increasing / Decreasing
      - humidity_trend: Stable / Increasing / Decreasing
      - recommendation: human-readable advice
      - source: "database" or "default" (when no data exists)
      - last_reading_at: ISO timestamp of the sensor reading used
    """
    latest = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .first()
    )

    if latest and latest.temperature is not None and latest.humidity is not None:
        temp = latest.temperature
        humidity = latest.humidity
        source = "database"
        last_reading_at = latest.recorded_at.isoformat() if latest.recorded_at else None
    else:
        # No sensor data available yet — return a "waiting for data" response
        return {
            "temperature": None,
            "humidity": None,
            "status": "Unknown",
            "risk_level": "Unknown",
            "score": None,
            "temperature_trend": "N/A",
            "humidity_trend": "N/A",
            "recommendation": "No sensor data available yet. Waiting for first reading.",
            "source": "none",
            "last_reading_at": None,
        }

    result = analyze(temp, humidity)
    result["source"] = source
    result["last_reading_at"] = last_reading_at
    return result