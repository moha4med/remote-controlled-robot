# app/ai/environmental/scoring.py
# Numerical scoring for environmental conditions (0-100).
# Starts at 100 and applies penalties based on how far conditions deviate from optimal.

# Optimal: temp 18-32°C, humidity 40-80%  → 0 penalty
# Mild:    temp 5-18°C or 32-38°C         → -10 penalty
# Moderate: humidity 20-40% or 80-90%     → -20 penalty
# Severe:  temp <5°C or >38°C             → -40 penalty
# Critical: humidity <20% or >90%         → -40 penalty


def score_environment(temp, humidity):
    """Score environmental conditions from 0 (dangerous) to 100 (perfect)."""
    score = 100

    # --- Temperature penalties ---
    if temp is not None:
        if temp < 5 or temp > 38:
            score -= 40  # Critical
        elif temp < 18 or temp > 32:
            score -= 20  # Warning zone
        # 18-32°C: optimal, no penalty

    # --- Humidity penalties ---
    if humidity is not None:
        if humidity < 20 or humidity > 90:
            score -= 40  # Critical
        elif humidity < 40 or humidity > 80:
            score -= 20  # Warning zone
        # 40-80%: optimal, no penalty

    return max(score, 0)