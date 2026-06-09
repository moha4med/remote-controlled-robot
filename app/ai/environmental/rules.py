# app/ai/environmental/rules.py
# Rule-based evaluation of environmental conditions.
# Categorizes into: Optimal, Warning, Critical with recommendations.

# Optimal ranges: temp 18-32°C, humidity 40-80%
# Warning ranges:  temp 5-18°C or 32-38°C, humidity 20-40% or 80-90%
# Critical ranges: temp <5°C or >38°C, humidity <20% or >90%


def evaluate_environment(temp, humidity):
    """Evaluate environmental conditions and return status + recommendation."""
    # --- Critical conditions (immediate danger) ---
    if temp > 38 or temp < 5 or humidity < 20 or humidity > 90:
        reasons = []
        if temp > 38:
            reasons.append(f"temperature critically high ({temp:.1f}°C)")
        elif temp < 5:
            reasons.append(f"temperature critically low ({temp:.1f}°C)")
        if humidity > 90:
            reasons.append(f"humidity critically high ({humidity:.1f}%)")
        elif humidity < 20:
            reasons.append(f"humidity critically low ({humidity:.1f}%)")
        return {
            "status": "Critical",
            "risk_level": "High",
            "recommendation": f"CRITICAL: {', '.join(reasons)}. Immediate action required. "
                              f"Consider shutting down non-essential systems.",
        }

    # --- Warning conditions (approaching unsafe) ---
    warning_reasons = []
    if 32 < temp <= 38:
        warning_reasons.append(f"temperature elevated ({temp:.1f}°C)")
    elif 5 <= temp < 18:
        warning_reasons.append(f"temperature low ({temp:.1f}°C)")
    if 80 < humidity <= 90:
        warning_reasons.append(f"humidity elevated ({humidity:.1f}%)")
    elif 20 <= humidity < 40:
        warning_reasons.append(f"humidity low ({humidity:.1f}%)")

    if warning_reasons:
        return {
            "status": "Warning",
            "risk_level": "Medium",
            "recommendation": f"WARNING: {', '.join(warning_reasons)}. "
                              f"Increased monitoring recommended. Prepare contingency measures.",
        }

    # --- Optimal conditions ---
    return {
        "status": "Optimal",
        "risk_level": "Low",
        "recommendation": "Environmental conditions are within optimal range. "
                          "Suitable for all monitoring operations.",
    }