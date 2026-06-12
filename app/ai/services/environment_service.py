# app/ai/services/environment_service.py
# Service layer: fetches latest sensor data and runs the analysis engine.

from datetime import datetime, timezone

from app.ai.environmental.analyzer import analyze
from app.models.sensor_log import SensorLog
from app.ai.agriculture.risk_assessor import assess_agricultural_risk
from app.ai.prediction.predictor import get_environment_prediction


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
      - data_quality: "good" or "suspect" based on recent variability
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
    
        recent = (
            SensorLog.query
            .order_by(SensorLog.recorded_at.desc())
            .limit(30)
            .all()
        )
        recent_temps = [r.temperature for r in recent if r.temperature is not None]
        recent_humids = [r.humidity for r in recent if r.humidity is not None]
        
        data_quality = "good"
        if len(recent_temps) >= 5:
            mean_temp = sum(recent_temps) / len(recent_temps)
            # Sample standard deviation
            variance_temp = sum((t - mean_temp) ** 2 for t in recent_temps) / len(recent_temps)
            std_temp = variance_temp ** 0.5
            if std_temp > 0 and abs(temp - mean_temp) > 3 * std_temp:
                data_quality = "suspect"
                
        if len(recent_humids) >= 5:
            mean_humid = sum(recent_humids) / len(recent_humids)
            # Sample standard deviation
            variance_humid = sum((h - mean_humid) ** 2 for h in recent_humids) / len(recent_humids)
            std_humid = variance_humid ** 0.5
            if std_humid > 0 and abs(humidity - mean_humid) > 3 * std_humid:
                data_quality = "suspect"
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
            "data_quality": "none"
        }

    result = analyze(temp, humidity)
    result["source"] = source
    result["last_reading_at"] = last_reading_at
    result["data_quality"] = data_quality
    return result


def get_agricultural_risk():
    # a function that fetches current data, runs prediction, then runs risk assessment. Add the endpoint:
    
    # Fetch current data and trends
    analysis = get_environment_analysis()
    temp = analysis.get("temperature")
    humidity = analysis.get("humidity")
    temp_trend = analysis.get("temperature_trend")
    humidity_trend = analysis.get("humidity_trend")

    # Run prediction
    prediction = get_environment_prediction(hours_ahead=6)  # Predict 6 hours ahead
    
    # Run risk assessment
    risk_level = assess_agricultural_risk(temp, humidity, temp_trend, humidity_trend, prediction)

    return risk_level