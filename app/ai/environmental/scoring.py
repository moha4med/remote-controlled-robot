# app/ai/environmental/scoring.py
# Numerical scoring for environmental conditions (0-100).
# Starts at 100 and applies penalties based on how far conditions deviate from optimal.

# Optimal: temp 18-32°C, humidity 40-80%  → 0 penalty
# Mild:    temp 5-18°C or 32-38°C         → -10 penalty
# Moderate: humidity 20-40% or 80-90%     → -20 penalty
# Severe:  temp <5°C or >38°C             → -40 penalty
# Critical: humidity <20% or >90%         → -40 penalty


def score_environment(temp, humidity, temp_trend=None, humidity_trend=None):
    """Score environmental conditions from 0 (dangerous) to 100 (perfect).
    
    Args:
        temp: current temperature
        humidity: current humidity
        temp_trend: dict with 'direction and 'rate_per_hour' (from trends.py)
        humidity_trend: dict with 'direction and 'rate_per_hour'
    """
    score = 100

    # Temperature penalties
    if temp is not None:
        if temp < 5 or temp > 38:
            score -= 40  # Critical
        elif temp < 18 or temp > 32:
            score -= 20  # Warning zone
        # 18-32°C: optimal, no penalty

    # Humidity penalties
    if humidity is not None:
        if humidity < 20 or humidity > 90:
            score -= 40  # Critical
        elif humidity < 40 or humidity > 80:
            score -= 20  # Warning zone
        # 40-80%: optimal, no penalty
        
    # Temperature rate-of-change penalties
    if temp_trend and temp_trend.get("rate_per_hour") is not None:
        rate = abs(temp_trend["rate_per_hour"])
        if rate > 5.0:
            score -= 20 # Extremely rapid change — dangerous
        elif rate > 3.0:
            score -= 10 # Rapid change — concerning
        elif rate > 1.5:
            score -= 5 # Moderate change — monitor
            
    # Humidity rate-of-change penalties
    if humidity_trend and humidity_trend.get("rate_per_hour") is not None:
        rate = abs(humidity_trend["rate_per_hour"])
        if rate > 10.0:
            score -= 15
        elif rate > 5.0:
            score -= 8
        elif rate > 2.0:
            score -=4

    return max(score, 0)