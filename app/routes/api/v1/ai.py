# app/routes/api/v1/ai.py
# API routes for AI-powered features, including environmental analysis and object detection
# Enhanced with comprehensive debug logging for troubleshooting detection issues

from flask import Blueprint, jsonify, request
from app.ai.services.environment_service import get_environment_analysis, get_agricultural_risk
from app.ai.prediction.predictor import get_environment_prediction

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


@ai_bp.route("/environment", methods=["GET"])
def environment():
    analysis = get_environment_analysis()
    return jsonify(analysis)


@ai_bp.route("/prediction", methods=["GET"])
def ai_prediction():
    hours = request.args.get("hours", 1, type=int)
    hours = max(1, min(24, hours))  # Clamp to 1-24 hours
    prediction = get_environment_prediction(hours_ahead=hours)
    return jsonify(prediction)


@ai_bp.route("/agriculture/risk", methods=["GET"])
def ai_agriculture_risk():
    result = get_agricultural_risk()
    return jsonify(result)