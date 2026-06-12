# app/ai/agriculture/risk_assessor.py

import math


def assess_agricultural_risk(temp, humidity, temp_trend, humidity_trend, prediction=None):
    """
    Returns agricultural risk assessment with actionable recommendations.
    Combines current conditions, trends, and predictions.

    Args:
        temp (float): Current temperature.
        humidity (float): Current humidity.
        temp_trend (str): Temperature trend ('increasing', 'decreasing', or 'stable').
        humidity_trend (str): Humidity trend ('increasing', 'decreasing', or 'stable').
        prediction (str): Optional future condition prediction.

    Returns:
        dict: {
            "overall_risk": "Low" | "Medium" | "High" | "Critical",
            "risks": [
                {"type": "frost", "severity": "warning", "description": "..."},
                {"type": "heat_stress", "severity": "critical", "description": "..."},
                ...
            ],
            "recommendations": [
                "Irrigation recommended due to low humidity and rising temperatures.",
                "Avoid pesticide spraying due to high humidity.",
                ...
            ],
            "dew_point": 12.3,
            "conditions_summary": "Temp 25°C, Humidity 60%, Dew point 15.2°C"
        }
    """
    
    risks = []
    recommendations = []
    
    # Frost risk
    if temp < 2:
        risks.append({
            "type": "frost",
            "severity": "critical",
            "description": f"Current temperature is {temp:.1f}°C, which is below freezing. This poses a high risk of frost damage to crops."
        })
    elif temp < 5 and temp_trend['direction'] == "Decreasing":
        risks.append({
            "type": "frost",
            "severity": "warning",
            "description": f"Temperature dropping toward frost range and currently at {temp:.1f}°C. Frost risk is increasing."
        })
        
    # Heat stress ris
    if temp > 38:
        risks.append({
            "type": "heat_stress",
            "severity": "critical",
            "description": f"Extreme heat. Increase irrigation and apply shade to crops."
        })
    elif temp > 32 and humidity < 30:
        risks.append({
            "type": "heat_stress",
            "severity": "warning",
            "description": f"Hot and dry conditions. Monitor crops closely and consider irrigation."
        })
        
    # Fungal disease risk (high humidity + moderate temp)
    if humidity > 85 and 15 <= temp <= 28:
        risks.append({
            "type": "fungal",
            "severity": "warning",
            "description": f"High humidity and moderate temperature. Monitor for fungal disease."
        })
        
    # Drought risk
    if humidity < 20:
        risks.append({
            "type": "drought",
            "severity": "critical",
            "description": f"Extreme drought. Increase irrigation and apply water-saving techniques."
        })
    elif humidity < 30 and humidity_trend['direction'] == "Decreasing":
        risks.append({
            "type": "drought",
            "severity": "warning",
            "description": f"Drought risk is increasing. Monitor crops closely and consider irrigation."
        })
        
    # Irrigation recommendation
    if humidity < 30 and temp_trend['direction'] == "Increasing":
        recommendations.append(f"Irrigation recommended: low humidity and rising temperatures ")
        
    # Pesticide spraying conditions
    if humidity > 80 or temp > 35:
        recommendations.append(f"Avoid pesticide spraying: conditions unfavorable (high humidity or extreme heat).")
    elif 18 <= temp <= 28 and 40 <= humidity <= 70:
        recommendations.append("Good conditions for pesticide spraying.")
        
    # Dew point calculation
    # Magnus formula: dew_point = (b * α) / (a - α) where α = (a*T)/(b+T) + ln(RH/100)
    a, b = 17.27, 237.7
    alpha = (a * temp) / (b + temp) + math.log(humidity / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    
    # Overall risk level
    if any(r['severity'] == 'critical' for r in risks):
        overall = "Critical"
    elif len(risks) >= 2:
        overall = "High"
    elif len(risks) == 1:
        overall = "Medium"
    else:
        overall = "Low"
        
    return {
        "overall_risk": overall,
        "risks": risks,
        "recommendations": recommendations,
        "dew_point": round(dew_point, 1),
        "conditions_summary": f"Temp {temp}°C, Humidity {humidity}%, Dew point {dew_point:.1f}°C",
    }