# app/ai/environmental/scoring.py
# Define scoring logic for environmental conditions

def score_environment(temp, humidity):
    score = 100
    
    # Temperature scoring
    if temp < 5 or temp > 38:
        score -= 40
    elif temp >= 32 and temp <= 38:
        score -= 20
    elif temp >= 18 and temp <= 32:
        score -= 0
    else:
        score -= 10
    
    # Humidity scoring
    if humidity < 20 or humidity > 90:
        score -= 40
    elif (humidity >= 20 and humidity < 40) or (humidity > 80 and humidity <= 90):
        score -= 20
    
    return max(score, 0)