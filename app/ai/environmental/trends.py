# app/ai/environmental/trends.py
# Define functions to analyze trends in environmental data

from app.models.sensor_log import SensorLog


def _linear_regression(x_values, y_values):

    n = len(x_values)
    if n < 2:
        return 0, y_values[0] if y_values else 0, 0

    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    # Calculate slope
    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean)**2 for x in x_values)

    if denominator == 0:
        return 0, y_mean, 0

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Calculate R² = 1 - (SS_res / SS_tot)
    ss_res = sum(
        (y - (slope * x + intercept))**2 for x, y in zip(x_values, y_values))
    ss_tot = sum((y - y_mean)**2 for y in y_values)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return slope, intercept, r_squared


def get_temperature_trend(count=30):
    """Analyze temperature trend using linear regression on last N sensor readings."""
    readings = (SensorLog.query.order_by(
        SensorLog.recorded_at.desc()).limit(count).all())

    # Filter out None values and prepare data for regression
    valid_readings = [(r.recorded_at.timestamp(), r.temperature)
                      for r in readings if r.temperature is not None]

    if len(valid_readings) < 2:
        return {
            "direction": "Stable",
            "rate_per_hour": 0,
            "confidence": "Low",
            "r_squared": 0
        }

    # Convert timestamps to hours since first reading
    valid_readings.reverse()  # Oldest first
    start_time = valid_readings[0][0]
    x_hours = [(t - start_time) / 3600 for t, _ in valid_readings]
    y_temps = [temp for _, temp in valid_readings]

    slope, intercept, r_squared = _linear_regression(x_hours, y_temps)

    # Classify trend direction with thresholds
    if slope > 0.5:
        direction = "Increasing"
    elif slope < -0.5:
        direction = "Decreasing"
    else:
        direction = "Stable"

    # Confidence based on R² value and sample count
    if len(valid_readings) >= 10 and r_squared > 0.7:
        confidence = "High"
    elif len(valid_readings) >= 5 and r_squared > 0.5:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "direction": direction,
        "rate_per_hour": round(slope, 2),
        "confidence": confidence,
        "r_squared": round(r_squared, 3),
        "sample_count": len(valid_readings)
    }


def get_humidity_trend(count=30):
    """Analyze humidity trend from last N sensor readings."""
    readings = (SensorLog.query.order_by(
        SensorLog.recorded_at.desc()).limit(count).all())

    # Filter out None values and prepare data for regression
    valid_readings = [(r.recorded_at.timestamp(), r.humidity) for r in readings
                      if r.humidity is not None]

    if len(valid_readings) < 2:
        return {
            "direction": "Stable",
            "rate_per_hour": 0,
            "confidence": "Low",
            "r_squared": 0
        }

    # Convert timestamps to hours since first reading
    valid_readings.reverse()  # Oldest first
    start_time = valid_readings[0][0]
    x_hours = [(t - start_time) / 3600 for t, _ in valid_readings]
    y_humids = [humid for _, humid in valid_readings]

    slope, intercept, r_squared = _linear_regression(x_hours, y_humids)

    # Classify trend direction with thresholds
    if slope > 2.0:
        direction = "Increasing"
    elif slope < -2.0:
        direction = "Decreasing"
    else:
        direction = "Stable"

    # Confidence based on R² value and sample count
    if len(valid_readings) >= 10 and r_squared > 0.7:
        confidence = "High"
    elif len(valid_readings) >= 5 and r_squared > 0.5:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "direction": direction,
        "rate_per_hour": round(slope, 2),
        "confidence": confidence,
        "r_squared": round(r_squared, 3),
        "sample_count": len(valid_readings)
    }