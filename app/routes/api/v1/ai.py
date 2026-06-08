# app/routes/api/v1/ai.py
# API routes for AI-powered features, including environmental analysis and object detection

from flask import Blueprint, jsonify
from app.ai.services.environment_service import get_environment_analysis

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


@ai_bp.route("/environment", methods=["GET"])
def environment():
    analysis = get_environment_analysis()
    return jsonify(analysis)


@ai_bp.route("/detection", methods=["GET"])
def get_detection():
    pass