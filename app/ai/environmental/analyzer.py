# app/ai/environmental/analyzer.py
# Main analysis engine: combines rules, scoring, and trends into a single result.

from .rules import evaluate_environment
from .scoring import score_environment
from .trends import get_temperature_trend, get_humidity_trend


def analyze(temp, humidity):
    """Produce a complete environmental analysis from current sensor data."""
    # Rule-based classification
    rule_result = evaluate_environment(temp, humidity)

    # Numerical score (0-100)
    score = score_environment(temp, humidity)

    # Historical trend analysis (from DB)
    temp_trend = get_temperature_trend()
    humidity_trend = get_humidity_trend()

    # Build a contextual recommendation combining trends + rules
    trend_notes = []
    if temp_trend == "Increasing" and temp > 30:
        trend_notes.append(f"Temperature is rising ({temp_trend}) and already elevated ({temp:.1f}°C).")
    elif temp_trend == "Decreasing" and temp < 15:
        trend_notes.append(f"Temperature is falling ({temp_trend}) and already low ({temp:.1f}°C).")
    elif temp_trend != "Stable":
        trend_notes.append(f"Temperature trend: {temp_trend} (current: {temp:.1f}°C).")

    if humidity_trend == "Increasing" and humidity > 75:
        trend_notes.append(f"Humidity is rising ({humidity_trend}) and already high ({humidity:.1f}%).")
    elif humidity_trend == "Decreasing" and humidity < 30:
        trend_notes.append(f"Humidity is falling ({humidity_trend}) and already low ({humidity:.1f}%).")
    elif humidity_trend != "Stable":
        trend_notes.append(f"Humidity trend: {humidity_trend} (current: {humidity:.1f}%).")

    # Combine trend notes with rule-based recommendation
    if trend_notes:
        recommendation = " ".join(trend_notes) + " " + rule_result["recommendation"]
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