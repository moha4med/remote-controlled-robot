# app/ai/environmental/trends.py
# Define functions to analyze trends in environmental data

from app.models.sensor_log import SensorLog

def get_temperature_trend(count=30):
    """Analyze temperature trend from last N sensor readings."""
    readings = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .limit(count)
        .all()
    )

    if len(readings) < 2:
        return "Stable"

    # readings are DESC, so last element is oldest
    first_val = readings[-1].temperature  # oldest
    last_val = readings[0].temperature   # newest

    if first_val is None or last_val is None:
        return "Stable"

    diff = last_val - first_val
    if diff > 1.0:
        return "Increasing"
    elif diff < -1.0:
        return "Decreasing"
    else:
        return "Stable"

def get_humidity_trend(count=30):
    """Analyze humidity trend from last N sensor readings."""
    readings = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .limit(count)
        .all()
    )

    if len(readings) < 2:
        return "Stable"

    first_val = readings[-1].humidity  # oldest
    last_val = readings[0].humidity   # newest

    if first_val is None or last_val is None:
        return "Stable"

    diff = last_val - first_val
    if diff > 2.0:
        return "Increasing"
    elif diff < -2.0:
        return "Decreasing"
    else:
        return "Stable"