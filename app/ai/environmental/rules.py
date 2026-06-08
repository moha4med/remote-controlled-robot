# app/ai/environmental/rules.py
# This module defines the rules for evaluating environmental conditions based on
# temperature and humidity readings. It categorizes the environment into three
# levels: Optimal, Warning, and Critical, and provides recommendations for each level.


def evaluate_environment(temp, humidity):
    # Check critical conditions first
    if temp > 38 or temp < 5 or humidity < 20 or humidity > 90:
        return {
            "status":
            "Critical",
            "risk_level":
            "High",
            "recommendation":
            "Environmental conditions are dangerous. Immediate action required."
        }
    # Check warning conditions second
    elif (temp >= 32 and temp <= 38) or (humidity >= 20 and humidity < 90) or (
            humidity > 80 and humidity <= 90):
        return {
            "status":
            "Warning",
            "risk_level":
            "Medium",
            "recommendation":
            "Environmental conditions are approaching unsafe levels. Increased monitoring recommended."
        }
    # Otherwise Optimal (temp 18-32, humidity 40-80)
    else:
        return {
            "status":
            "Optimal",
            "risk_level":
            "Low",
            "recommendation":
            "Environmental conditions are suitable for monitoring operations."
        }