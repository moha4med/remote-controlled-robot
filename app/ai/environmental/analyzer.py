# app/ai/environmental/analyzer.py
# Main analysis engine: combines rules, scoring, and trends into a single result.

from .rules import evaluate_environment
from .scoring import score_environment
from .trends import get_temperature_trend, get_humidity_trend


def analyze(temp, humidity):
    """Produce a complete environmental analysis from current sensor data."""

    # Validate inputs
    if temp is None or humidity is None:
        return {
            "temperature": temp,
            "humidity": humidity,
            "status": "Unknown",
            "risk_level": "Unknown",
            "score": None,
            "temperature_trend": "Unknown",
            "humidity_trend": "Unknown",
            "recommendation":
            "Missing temperature or humidity data. Unable to analyze environment.",
            "source": "invalid",
            "last_reading_at": None,
            "data_quality": "missing"
        }
    elif not (isinstance(temp,
                         (int, float)) and isinstance(humidity, (int, float))):
        return {
            "temperature": temp,
            "humidity": humidity,
            "status": "Invalid",
            "risk_level": "Invalid",
            "score": None,
            "temperature_trend": "Unknown",
            "humidity_trend": "Unknown",
            "recommendation":
            "Temperature and humidity must be numeric values.",
            "source": "invalid",
            "last_reading_at": None,
            "data_quality": "invalid"
        }
    elif not (-40 <= temp <= 100 and 0 <= humidity <= 100):
        temp = max(-40, min(60, float(temp)))
        humidity = max(0, min(100, float(humidity)))

    # Rule-based classification
    rule_result = evaluate_environment(temp, humidity)

    # Historical trend analysis (from DB)
    temp_trend = get_temperature_trend()
    humidity_trend = get_humidity_trend()
    
    # Numerical score (0-100)
    score = score_environment(temp, humidity, temp_trend, humidity_trend)

    # Build a contextual recommendation combining trends + rules
    trend_notes = []
    if temp_trend["direction"] == "Increasing" and temp > 30:
        trend_notes.append(
            f"Temperature rising at ({temp_trend['rate_per_hour']}) and already elevated ({temp:.1f}°C)."
        )
    elif temp_trend["direction"] == "Decreasing" and temp < 15:
        trend_notes.append(
            f"Temperature falling at ({temp_trend['rate_per_hour']}) and already low ({temp:.1f}°C)."
        )
    elif temp_trend["direction"] != "Stable":
        trend_notes.append(
            f"Temperature trend: temp_trend['direction'] at {temp_trend['rate_per_hour']} (current: {temp:.1f}°C).")

    if humidity_trend["direction"] == "Increasing" and humidity > 75:
        trend_notes.append(
            f"Humidity rising at ({humidity_trend['rate_per_hour']}) and already high ({humidity:.1f}%)."
        )
    elif humidity_trend["direction"] == "Decreasing" and humidity < 30:
        trend_notes.append(
            f"Humidity falling at ({humidity_trend['rate_per_hour']}) and already low ({humidity:.1f}%)."
        )
    elif humidity_trend["direction"] != "Stable":
        trend_notes.append(
            f"Humidity trend: humidity_trend['direction'] at {humidity_trend['rate_per_hour']} (current: {humidity:.1f}%).")

    # Combine trend notes with rule-based recommendation
    if trend_notes:
        recommendation = " ".join(
            trend_notes) + " " + rule_result["recommendation"]
    else:
        recommendation = rule_result["recommendation"]

    return {
        "temperature": temp,
        "humidity": humidity,
        "status": rule_result["status"],
        "risk_level": rule_result["risk_level"],
        "score": score,
        "temperature_trend": temp_trend,
        "humidity_trend": humidity_trend,
        "recommendation": recommendation.strip(),
    }