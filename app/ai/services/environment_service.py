# app/ai/services/environment_service.py
# Service layer to provide environmental analysis results to API routes

from app.ai.environmental.analyzer import analyze
from app.models.sensor_log import SensorLog

def get_environment_analysis():
    # Get the latest sensor reading
    latest = (
        SensorLog.query
        .order_by(SensorLog.recorded_at.desc())
        .first()
    )
    
    if latest:
        temp = latest.temperature
        humidity = latest.humidity
    else:
        temp = 25.0
        humidity = 50.0
    
    return analyze(
        temp,
        humidity
    )