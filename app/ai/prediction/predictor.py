# app/ai/prediction/predictor.py

from app.models.sensor_log import SensorLog
from app.ai.environmental.trends import get_temperature_trend, get_humidity_trend


def get_environment_prediction(hours_ahead=1):
    """Predict temperature and humidity N hours into the future based on current trends."""

    temp_trend = get_temperature_trend()
    humidity_trend = get_humidity_trend()

    # Get current values
    latest = SensorLog.query.order_by(SensorLog.recorded_at.desc()).first()

    # Extrapolate: future = current + slope * hours
    predicted_temp = latest.temperature + temp_trend[
        'rate_per_hour'] * hours_ahead
    predicted_humidity = latest.humidity + humidity_trend[
        'rate_per_hour'] * hours_ahead

    # Clamp to physical ranges
    predicted_temp = max(-40, min(60, predicted_temp))
    predicted_humidity = max(0, min(100, predicted_humidity))

    # Determine confidence
    prediction_confidence = "Unknown"
    if temp_trend['confidence'] == humidity_trend['confidence']:
        prediction_confidence = temp_trend['confidence']
    elif temp_trend['confidence'] == "Low" or humidity_trend['confidence'] == "Low":
        prediction_confidence = "Low"
    elif temp_trend['confidence'] == "High" or humidity_trend['confidence'] == "High":
        prediction_confidence = "High"
    else:
        prediction_confidence = "Medium"

    return {
        "current": {
            "temperature": latest.temperature,
            "humidity": latest.humidity
        },
        "predicted": {
            "temperature": round(predicted_temp, 1),
            "humidity": round(predicted_humidity, 1)
        },
        "hours_ahead": hours_ahead,
        "confidence": prediction_confidence,
        "source": "simple_trend_extrapolation"
    }
