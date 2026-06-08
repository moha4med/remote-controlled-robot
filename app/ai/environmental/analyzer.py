# app/ai/environmental/analyzer.py
# Main logic to analyze environmental data and provide insights

from .rules import evaluate_environment
from .scoring import score_environment
from .trends import analyze_trends

def analyze(temp, humidity):
    # Rule-based classification
    rule_result = evaluate_environment(temp, humidity)

    # Environmental scoring
    score = score_environment(temp, humidity)

    # Historical trend analysis
    temp_trend = get_temperature_trend()
    humidity_trend = get_humidity_trend()
    
    recommendation = ""
    if temp_trend == "Increasing" or rule_result["risk_level"] != "Critical":
        recommendation += "Temperature is rising. "
    elif temp_trend == "Decreasing" and temp < 10:
        recommendation += "Temperature is falling. Monitor for potential cold conditions."
        
    if humidity_trend == "Increasing" or rule_result["risk_level"] != "Critical":
        recommendation += "Humidity is rising. "
    elif humidity_trend == "Decreasing" and humidity < 30:
        recommendation += "Humidity is falling. Monitor for potential dry conditions."
        
    recommendation += rule_result["recommendation"]

    return {
        "temperature": temp,
        "humidity": humidity,
        "status": rule_result["status"],
        "risk_level": rule_result["risk_level"],
        "score": score,
        "temperature_trend": temp_trend,
        "humidity_trend": humidity_trend,
        "recommendation": recommendation
    }